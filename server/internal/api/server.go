package api

import (
"context"
"encoding/json"
"fmt"
"io"
"log"
"net/http"
"time"

"github.com/gorilla/mux"
"github.com/gorilla/websocket"
"github.com/networkmemories/nm-play-server/internal/relay"
)

var upgrader = websocket.Upgrader{
CheckOrigin: func(r *http.Request) bool { return true },
}

type Server struct {
addr    string
hub     *relay.Hub
ws      *WSHub
authURL string
}

func NewServer(addr string, hub *relay.Hub, authURL string) *Server {
s := &Server{addr: addr, hub: hub, ws: NewWSHub(), authURL: authURL}
hub.Notifier = func(event string, data interface{}) {
s.ws.Broadcast(event, data)
}
return s
}

func (s *Server) Run() {
go s.ws.Run()
r := mux.NewRouter()
r.Use(corsMiddleware)

// Public
r.HandleFunc("/health", s.handleHealth).Methods("GET", "OPTIONS")
r.HandleFunc("/stats", s.handleStats).Methods("GET", "OPTIONS")
r.HandleFunc("/lobbies", s.handleGetLobbies).Methods("GET", "OPTIONS")

// Auth required
r.HandleFunc("/connect", s.authMiddleware(s.handleConnect)).Methods("POST", "OPTIONS")
r.HandleFunc("/disconnect", s.authMiddleware(s.handleDisconnect)).Methods("POST", "OPTIONS")
r.HandleFunc("/heartbeat", s.authMiddleware(s.handleHeartbeat)).Methods("POST", "OPTIONS")
r.HandleFunc("/lobbies", s.authMiddleware(s.handleCreateLobby)).Methods("POST", "OPTIONS")
r.HandleFunc("/lobbies/{id}/join", s.authMiddleware(s.handleJoinLobby)).Methods("POST", "OPTIONS")
r.HandleFunc("/lobbies/{id}/leave", s.authMiddleware(s.handleLeaveLobby)).Methods("POST", "OPTIONS")

// WebSocket
r.HandleFunc("/ws", s.handleWS)

log.Printf("[API] Listening on %s", s.addr)
if err := http.ListenAndServe(s.addr, r); err != nil {
log.Fatalf("[API] Server error: %v", err)
}
}

// ── Auth middleware ──────────────────────────────────────────────────────────

type contextKey string
const clientKey contextKey = "client"

func (s *Server) authMiddleware(next http.HandlerFunc) http.HandlerFunc {
return func(w http.ResponseWriter, r *http.Request) {
if r.Method == "OPTIONS" {
w.WriteHeader(200)
return
}
token := r.Header.Get("Authorization")
if token == "" {
jsonErr(w, "token required", 401)
return
}
if len(token) > 7 && token[:7] == "Bearer " {
token = token[7:]
}
// Validate token against NM site
client, err := s.validateNMToken(token)
if err != nil {
jsonErr(w, "invalid token: "+err.Error(), 401)
return
}
// Set client in hub if not already there
s.hub.EnsureClient(client)
r = r.WithContext(context.WithValue(r.Context(), clientKey, client))
next(w, r)
}
}

func (s *Server) validateNMToken(token string) (*relay.Client, error) {
req, _ := http.NewRequest("GET", s.authURL+"/api/nmplay/validate", nil)
req.Header.Set("Authorization", "Bearer "+token)
resp, err := http.DefaultClient.Do(req)
if err != nil {
return nil, fmt.Errorf("auth server unreachable")
}
defer resp.Body.Close()
body, _ := io.ReadAll(resp.Body)
var data map[string]interface{}
json.Unmarshal(body, &data)
if valid, _ := data["valid"].(bool); !valid {
return nil, fmt.Errorf("invalid token")
}
username, _ := data["username"].(string)
client := &relay.Client{
ID:       token[:16],
Username: username,
Token:    token,
}
return client, nil
}

// ── Handlers ─────────────────────────────────────────────────────────────────

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
json.NewEncoder(w).Encode(map[string]interface{}{
"status": "ok",
"server": "NM-Play",
"time":   time.Now().Unix(),
})
}

func (s *Server) handleStats(w http.ResponseWriter, r *http.Request) {
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(s.hub.GetStats())
}

func (s *Server) handleGetLobbies(w http.ResponseWriter, r *http.Request) {
w.Header().Set("Content-Type", "application/json")
platform := r.URL.Query().Get("platform")
json.NewEncoder(w).Encode(s.hub.GetLobbies(platform))
}

func (s *Server) handleConnect(w http.ResponseWriter, r *http.Request) {
client := clientFromContext(r.Context())
var body struct {
Platform string `json:"platform"`
LanIP    string `json:"lan_ip"`
}
json.NewDecoder(r.Body).Decode(&body)
client.Platform = body.Platform
client.LastSeen = time.Now()
s.hub.Register(client)
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(map[string]interface{}{
"ok":       true,
"clientID": client.ID,
"username": client.Username,
})
}

func (s *Server) handleDisconnect(w http.ResponseWriter, r *http.Request) {
client := clientFromContext(r.Context())
s.hub.Unregister(client)
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(map[string]interface{}{"ok": true})
}

func (s *Server) handleHeartbeat(w http.ResponseWriter, r *http.Request) {
client := clientFromContext(r.Context())
s.hub.UpdateHeartbeat(client.ID)
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(map[string]interface{}{"ok": true})
}

func (s *Server) handleCreateLobby(w http.ResponseWriter, r *http.Request) {
client := clientFromContext(r.Context())
var body struct {
Name       string `json:"name"`
Platform   string `json:"platform"`
Game       string `json:"game"`
Password   string `json:"password"`
MaxPlayers int    `json:"maxPlayers"`
}
json.NewDecoder(r.Body).Decode(&body)
if body.Name == "" || body.Platform == "" {
jsonErr(w, "name and platform required", 400)
return
}
if body.MaxPlayers <= 0 {
body.MaxPlayers = 8
}
lobby, err := s.hub.CreateLobby(body.Name, body.Platform, body.Game, client.ID, body.Password, body.MaxPlayers)
if err != nil {
jsonErr(w, err.Error(), 500)
return
}
// Host auto-joins
s.hub.JoinLobby(lobby.ID, client.ID, body.Password)
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(map[string]interface{}{
"ok":    true,
"lobby": lobbyToMap(lobby, client.ID),
})
}

func (s *Server) handleJoinLobby(w http.ResponseWriter, r *http.Request) {
client := clientFromContext(r.Context())
vars := mux.Vars(r)
lobbyID := vars["id"]
var body struct {
Password string `json:"password"`
}
json.NewDecoder(r.Body).Decode(&body)
err := s.hub.JoinLobby(lobbyID, client.ID, body.Password)
if err != nil {
jsonErr(w, err.Error(), 400)
return
}
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(map[string]interface{}{"ok": true})
}

func (s *Server) handleLeaveLobby(w http.ResponseWriter, r *http.Request) {
client := clientFromContext(r.Context())
s.hub.LeaveLobby(client.ID)
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(map[string]interface{}{"ok": true})
}

func (s *Server) handleWS(w http.ResponseWriter, r *http.Request) {
conn, err := upgrader.Upgrade(w, r, nil)
if err != nil {
log.Printf("[WS] Upgrade error: %v", err)
return
}
s.ws.AddClient(conn)
}

// ── Helpers ──────────────────────────────────────────────────────────────────

func jsonErr(w http.ResponseWriter, msg string, code int) {
w.Header().Set("Content-Type", "application/json")
w.WriteHeader(code)
json.NewEncoder(w).Encode(map[string]interface{}{"error": msg})
}

func lobbyToMap(l *relay.Lobby, currentClientID string) map[string]interface{} {
players := []map[string]interface{}{}
for _, p := range l.GetPlayers() {
players = append(players, map[string]interface{}{
"id":       p.ID,
"username": p.Username,
"avatar":   p.Avatar,
"isHost":   p.ID == l.HostID,
"isMe":     p.ID == currentClientID,
})
}
return map[string]interface{}{
"id":         l.ID,
"name":       l.Name,
"platform":   l.Platform,
"game":       l.Game,
"hostID":     l.HostID,
"players":    players,
"maxPlayers": l.MaxPlayer,
"private":    l.IsPrivate(),
"createdAt":  l.CreatedAt,
}
}

func corsMiddleware(next http.Handler) http.Handler {
return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
w.Header().Set("Access-Control-Allow-Origin", "*")
w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
w.Header().Set("Content-Type", "application/json")
if r.Method == "OPTIONS" {
w.WriteHeader(200)
return
}
next.ServeHTTP(w, r)
})
}

func clientFromContext(ctx context.Context) *relay.Client {
if c, ok := ctx.Value(clientKey).(*relay.Client); ok {
return c
}
return &relay.Client{}
}
