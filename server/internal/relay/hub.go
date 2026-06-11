package relay

import (
"log"
"net"
"sync"
"time"

"fmt"
"github.com/google/uuid"
)

const (
PlatformSwitch   = "switch"
PlatformPS2      = "ps2"
PlatformPS3      = "ps3"
PlatformXbox     = "xbox"
PlatformXbox360  = "xbox360"
PlatformGameCube = "gamecube"
PlatformWii      = "wii"
PlatformPSP      = "psp"
PlatformVita     = "vita"
PlatformXboxOne  = "xboxone"
PlatformSwitch2  = "switch2"

HeartbeatInterval = 30 * time.Second
HeartbeatTimeout  = 90 * time.Second
)

// Client represents a connected player
type Client struct {
ID        string
UserID    int
Username  string
Avatar    string
Platform  string
LanIP     net.IP
RemoteIP  *net.UDPAddr
LobbyID   string
ConnectAt time.Time
LastSeen  time.Time
TCPConn   net.Conn
Send      chan Packet
	Token     string
}

type Packet struct {
Data     []byte
From     *Client
Platform string
}

// Lobby represents a game session
type Lobby struct {
ID        string
Name      string
Platform  string
Game      string
HostID    string
Password  string // empty = public
Players   map[string]*Client
MaxPlayer int
CreatedAt time.Time
mu        sync.RWMutex
}

func (l *Lobby) PlayerCount() int {
l.mu.RLock()
defer l.mu.RUnlock()
return len(l.Players)
}

func (l *Lobby) IsPrivate() bool {
return l.Password != ""
}

func (l *Lobby) CheckPassword(pw string) bool {
if l.Password == "" {
return true
}
return l.Password == pw
}

func (l *Lobby) AddPlayer(c *Client) {
l.mu.Lock()
defer l.mu.Unlock()
l.Players[c.ID] = c
c.LobbyID = l.ID
}

func (l *Lobby) RemovePlayer(id string) {
l.mu.Lock()
defer l.mu.Unlock()
if c, ok := l.Players[id]; ok {
c.LobbyID = ""
}
delete(l.Players, id)
}

func (l *Lobby) GetPlayers() []*Client {
l.mu.RLock()
defer l.mu.RUnlock()
players := make([]*Client, 0, len(l.Players))
for _, c := range l.Players {
players = append(players, c)
}
return players
}

// Hub manages all clients and lobbies
type Hub struct {
clients    map[string]*Client
lobbies    map[string]*Lobby
register   chan *Client
unregister chan *Client
broadcast  chan Packet
mu         sync.RWMutex
Notifier   func(string, interface{})
}

func NewHub() *Hub {
return &Hub{
clients:    make(map[string]*Client),
lobbies:    make(map[string]*Lobby),
register:   make(chan *Client, 64),
unregister: make(chan *Client, 64),
broadcast:  make(chan Packet, 256),
}
}

func (h *Hub) Run() {
ticker := time.NewTicker(HeartbeatInterval)
defer ticker.Stop()

for {
select {
case c := <-h.register:
h.mu.Lock()
h.clients[c.ID] = c
h.mu.Unlock()
log.Printf("[Hub] Client connected: %s (%s)", c.Username, c.ID)

case c := <-h.unregister:
h.mu.Lock()
if _, ok := h.clients[c.ID]; ok {
delete(h.clients, c.ID)
// Remove from lobby
if c.LobbyID != "" {
if lobby, ok := h.lobbies[c.LobbyID]; ok {
lobby.RemovePlayer(c.ID)
// Delete lobby if empty
if lobby.PlayerCount() == 0 {
delete(h.lobbies, c.LobbyID)
log.Printf("[Hub] Lobby deleted (empty): %s", lobby.Name)
} else if lobby.HostID == c.ID {
// Transfer host to first remaining player
players := lobby.GetPlayers()
if len(players) > 0 {
lobby.HostID = players[0].ID
log.Printf("[Hub] Host transferred to: %s", players[0].Username)
}
}
}
}
close(c.Send)
log.Printf("[Hub] Client disconnected: %s (%s)", c.Username, c.ID)
}
h.mu.Unlock()

case pkt := <-h.broadcast:
h.mu.RLock()
if pkt.From != nil && pkt.From.LobbyID != "" {
if lobby, ok := h.lobbies[pkt.From.LobbyID]; ok {
for _, c := range lobby.GetPlayers() {
if c.ID != pkt.From.ID {
select {
case c.Send <- pkt:
default:
log.Printf("[Hub] Send buffer full for %s", c.Username)
}
}
}
}
}
h.mu.RUnlock()

case <-ticker.C:
h.checkHeartbeats()
}
}
}

func (h *Hub) checkHeartbeats() {
h.mu.Lock()
defer h.mu.Unlock()
now := time.Now()
for id, c := range h.clients {
if now.Sub(c.LastSeen) > HeartbeatTimeout {
log.Printf("[Hub] Client timeout: %s", c.Username)
delete(h.clients, id)
if c.LobbyID != "" {
if lobby, ok := h.lobbies[c.LobbyID]; ok {
lobby.RemovePlayer(id)
if lobby.PlayerCount() == 0 {
delete(h.lobbies, c.LobbyID)
}
}
}
close(c.Send)
}
}
}

// CreateLobby creates a new lobby
func (h *Hub) CreateLobby(name, platform, game, hostID, password string, maxPlayers int) (*Lobby, error) {
h.mu.Lock()
defer h.mu.Unlock()

lobby := &Lobby{
ID:        uuid.New().String(),
Name:      name,
Platform:  platform,
Game:      game,
HostID:    hostID,
Password:  password,
Players:   make(map[string]*Client),
MaxPlayer: maxPlayers,
CreatedAt: time.Now(),
}
h.lobbies[lobby.ID] = lobby
log.Printf("[Hub] Lobby created: %s (%s) by %s", name, platform, hostID)
return lobby, nil
}

// JoinLobby adds a client to a lobby
func (h *Hub) JoinLobby(lobbyID, clientID, password string) error {
h.mu.Lock()
defer h.mu.Unlock()

lobby, ok := h.lobbies[lobbyID]
if !ok {
return fmt.Errorf("lobby not found")
}
if lobby.PlayerCount() >= lobby.MaxPlayer {
return fmt.Errorf("lobby full")
}
if !lobby.CheckPassword(password) {
return fmt.Errorf("wrong password")
}
client, ok := h.clients[clientID]
if !ok {
return fmt.Errorf("client not found")
}
// Leave current lobby first
if client.LobbyID != "" {
if old, ok := h.lobbies[client.LobbyID]; ok {
old.RemovePlayer(clientID)
if old.PlayerCount() == 0 {
delete(h.lobbies, client.LobbyID)
}
}
}
lobby.AddPlayer(client)
return nil
}

// LeaveLobby removes a client from their lobby
func (h *Hub) LeaveLobby(clientID string) {
h.mu.Lock()
defer h.mu.Unlock()
client, ok := h.clients[clientID]
if !ok || client.LobbyID == "" {
return
}
if lobby, ok := h.lobbies[client.LobbyID]; ok {
lobby.RemovePlayer(clientID)
if lobby.PlayerCount() == 0 {
delete(h.lobbies, client.LobbyID)
} else if lobby.HostID == clientID {
players := lobby.GetPlayers()
if len(players) > 0 {
lobby.HostID = players[0].ID
}
}
}
}

// GetStats returns current server stats
func (h *Hub) GetStats() map[string]interface{} {
h.mu.RLock()
defer h.mu.RUnlock()

byPlatform := make(map[string]int)
for _, c := range h.clients {
byPlatform[c.Platform]++
}

return map[string]interface{}{
"online":     len(h.clients),
"lobbies":    len(h.lobbies),
"byPlatform": byPlatform,
}
}

// GetLobbies returns lobbies filtered by platform
func (h *Hub) GetLobbies(platform string) []map[string]interface{} {
h.mu.RLock()
defer h.mu.RUnlock()

result := []map[string]interface{}{}
for _, l := range h.lobbies {
if platform != "" && l.Platform != platform {
continue
}
players := []map[string]interface{}{}
for _, p := range l.GetPlayers() {
players = append(players, map[string]interface{}{
"id":       p.ID,
"username": p.Username,
"avatar":   p.Avatar,
})
}
result = append(result, map[string]interface{}{
"id":         l.ID,
"name":       l.Name,
"platform":   l.Platform,
"game":       l.Game,
"hostID":     l.HostID,
"players":    players,
"maxPlayers": l.MaxPlayer,
"private":    l.IsPrivate(),
"createdAt":  l.CreatedAt,
})
}
return result
}

// Register/Unregister helpers
func (h *Hub) Register(c *Client) {
h.register <- c
}

func (h *Hub) Unregister(c *Client) {
h.unregister <- c
}

func (h *Hub) Broadcast(pkt Packet) {
h.broadcast <- pkt
}

func (h *Hub) UpdateHeartbeat(clientID string) {
h.mu.Lock()
defer h.mu.Unlock()
if c, ok := h.clients[clientID]; ok {
c.LastSeen = time.Now()
}
}
// NewClient creates a new authenticated client
func NewClient(id, username, token string) *Client {
return &Client{
ID:        id,
Username:  username,
Token:     token,
ConnectAt: time.Now(),
LastSeen:  time.Now(),
Send:      make(chan Packet, 64),
}
}

// NewRelayClient creates a client from relay connection (no auth)
func NewRelayClient(platform string, remoteAddr *net.UDPAddr, lanIP net.IP) *Client {
id := remoteAddr.String()
return &Client{
ID:        id,
Username:  "guest_" + id,
Platform:  platform,
RemoteIP:  remoteAddr,
LanIP:     lanIP,
ConnectAt: time.Now(),
LastSeen:  time.Now(),
Send:      make(chan Packet, 64),
}
}

// EnsureClient adds client to hub if not already present
func (h *Hub) EnsureClient(c *Client) {
h.mu.Lock()
defer h.mu.Unlock()
if _, ok := h.clients[c.ID]; !ok {
h.clients[c.ID] = c
log.Printf("[Hub] EnsureClient: %s", c.Username)
} else {
h.clients[c.ID].LastSeen = time.Now()
}
}