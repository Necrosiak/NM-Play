package api

import (
"encoding/json"
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
addr string
hub  *relay.Hub
ws   *WSHub
}

func NewServer(addr string, hub *relay.Hub) *Server {
s := &Server{addr: addr, hub: hub, ws: NewWSHub()}
hub.Notifier = func(event string, data interface{}) {
s.ws.Broadcast(event, data)
}
return s
}

func (s *Server) Run() {
go s.ws.Run()
r := mux.NewRouter()
r.Use(corsMiddleware)
r.HandleFunc("/health", s.handleHealth).Methods("GET")
r.HandleFunc("/stats", s.handleStats).Methods("GET")
r.HandleFunc("/lobbies", s.handleGetLobbies).Methods("GET")
r.HandleFunc("/lobbies", s.handleCreateLobby).Methods("POST")
r.HandleFunc("/lobbies/{id}/join", s.handleJoinLobby).Methods("POST")
r.HandleFunc("/ws", s.handleWS)
log.Printf("[API] Listening on %s", s.addr)
if err := http.ListenAndServe(s.addr, r); err != nil {
log.Fatalf("[API] Server error: %v", err)
}
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(map[string]interface{}{
"status": "ok",
"time":   time.Now().Unix(),
"server": "NM-Play",
})
}

func (s *Server) handleStats(w http.ResponseWriter, r *http.Request) {
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(s.hub.GetStats())
}

func (s *Server) handleGetLobbies(w http.ResponseWriter, r *http.Request) {
platform := r.URL.Query().Get("platform")
lobbies := s.hub.GetLobbies(platform)
w.Header().Set("Content-Type", "application/json")
var result []map[string]interface{}
for _, l := range lobbies {
result = append(result, lobbyToMap(l))
}
if result == nil {
result = []map[string]interface{}{}
}
json.NewEncoder(w).Encode(result)
}

func (s *Server) handleCreateLobby(w http.ResponseWriter, r *http.Request) {
var req struct {
Name       string `json:"name"`
Game       string `json:"game"`
Platform   string `json:"platform"`
Username   string `json:"username"`
MaxPlayers int    `json:"max_players"`
}
if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
http.Error(w, "Invalid request", 400)
return
}
if req.MaxPlayers == 0 {
req.MaxPlayers = 8
}
host := relay.NewClient(req.Platform, nil, nil)
host.Username = req.Username
s.hub.Register(host)
lobby := s.hub.CreateLobby(host, req.Name, req.Game, req.MaxPlayers)
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(lobbyToMap(lobby))
}

func (s *Server) handleJoinLobby(w http.ResponseWriter, r *http.Request) {
vars := mux.Vars(r)
var req struct {
Username string `json:"username"`
Platform string `json:"platform"`
}
if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
http.Error(w, "Invalid request", 400)
return
}
client := relay.NewClient(req.Platform, nil, nil)
client.Username = req.Username
s.hub.Register(client)
lobby, ok := s.hub.JoinLobby(client, vars["id"])
if !ok {
http.Error(w, "Lobby not found or full", 404)
return
}
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(lobbyToMap(lobby))
}

func (s *Server) handleWS(w http.ResponseWriter, r *http.Request) {
conn, err := upgrader.Upgrade(w, r, nil)
if err != nil {
return
}
s.ws.AddClient(conn)
}

func lobbyToMap(l *relay.Lobby) map[string]interface{} {
players := []map[string]interface{}{}
for _, c := range l.Players {
players = append(players, map[string]interface{}{
"id":       c.ID,
"username": c.Username,
"platform": c.Platform,
})
}
return map[string]interface{}{
"id":         l.ID,
"name":       l.Name,
"platform":   l.Platform,
"game":       l.Game,
"players":    players,
"maxPlayers": l.MaxPlayer,
"createdAt":  l.CreatedAt,
}
}

func corsMiddleware(next http.Handler) http.Handler {
return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
w.Header().Set("Access-Control-Allow-Origin", "*")
w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
if r.Method == "OPTIONS" {
w.WriteHeader(200)
return
}
next.ServeHTTP(w, r)
})
}
