package relay

import (
"log"
"net"
"sync"
"time"

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
)

type Client struct {
ID        string
Username  string
Platform  string
LanIP     net.IP
RemoteIP  *net.UDPAddr
LobbyID   string
ConnectAt time.Time
LastSeen  time.Time
TCPConn   net.Conn
Send      chan Packet
}

type Packet struct {
Data     []byte
From     *Client
Platform string
}

type Lobby struct {
ID        string
Name      string
Platform  string
Game      string
HostID    string
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

func (l *Lobby) AddPlayer(c *Client) {
l.mu.Lock()
defer l.mu.Unlock()
l.Players[c.ID] = c
c.LobbyID = l.ID
}

func (l *Lobby) RemovePlayer(id string) {
l.mu.Lock()
defer l.mu.Unlock()
delete(l.Players, id)
}

type Hub struct {
clients    map[string]*Client
lobbies    map[string]*Lobby
register   chan *Client
unregister chan *Client
broadcast  chan Packet
mu         sync.RWMutex
Notifier   func(event string, data interface{})
}

func NewHub() *Hub {
return &Hub{
clients:    make(map[string]*Client),
lobbies:    make(map[string]*Lobby),
register:   make(chan *Client, 256),
unregister: make(chan *Client, 256),
broadcast:  make(chan Packet, 4096),
Notifier:   func(event string, data interface{}) {},
}
}

func NewClient(platform string, remoteIP *net.UDPAddr, lanIP net.IP) *Client {
return &Client{
ID:        uuid.New().String(),
Platform:  platform,
RemoteIP:  remoteIP,
LanIP:     lanIP,
ConnectAt: time.Now(),
LastSeen:  time.Now(),
Send:      make(chan Packet, 256),
}
}

func (h *Hub) Register(c *Client)   { h.register <- c }
func (h *Hub) Unregister(c *Client) { h.unregister <- c }
func (h *Hub) Broadcast(pkt Packet) { h.broadcast <- pkt }

func (h *Hub) Run() {
ticker := time.NewTicker(30 * time.Second)
defer ticker.Stop()
for {
select {
case c := <-h.register:
h.mu.Lock()
h.clients[c.ID] = c
h.mu.Unlock()
log.Printf("[Hub] Connected: %s (%s)", c.ID, c.Platform)
h.Notifier("player_connect", c)
case c := <-h.unregister:
h.mu.Lock()
if _, ok := h.clients[c.ID]; ok {
delete(h.clients, c.ID)
if c.LobbyID != "" {
if lobby, ok := h.lobbies[c.LobbyID]; ok {
lobby.RemovePlayer(c.ID)
if lobby.PlayerCount() == 0 {
delete(h.lobbies, c.LobbyID)
}
}
}
}
h.mu.Unlock()
h.Notifier("player_disconnect", c)
case pkt := <-h.broadcast:
h.relayPacket(pkt)
case <-ticker.C:
h.cleanup()
}
}
}

func (h *Hub) relayPacket(pkt Packet) {
h.mu.RLock()
defer h.mu.RUnlock()
from := pkt.From
if from == nil {
return
}
if from.LobbyID != "" {
if lobby, ok := h.lobbies[from.LobbyID]; ok {
lobby.mu.RLock()
for id, c := range lobby.Players {
if id != from.ID {
select {
case c.Send <- pkt:
default:
}
}
}
lobby.mu.RUnlock()
return
}
}
for id, c := range h.clients {
if id != from.ID && c.Platform == from.Platform {
select {
case c.Send <- pkt:
default:
}
}
}
}

func (h *Hub) cleanup() {
h.mu.Lock()
defer h.mu.Unlock()
cutoff := time.Now().Add(-2 * time.Minute)
for id, c := range h.clients {
if c.LastSeen.Before(cutoff) {
delete(h.clients, id)
}
}
}

func (h *Hub) CreateLobby(host *Client, name, game string, maxPlayers int) *Lobby {
lobby := &Lobby{
ID:        uuid.New().String(),
Name:      name,
Platform:  host.Platform,
Game:      game,
HostID:    host.ID,
Players:   make(map[string]*Client),
MaxPlayer: maxPlayers,
CreatedAt: time.Now(),
}
lobby.AddPlayer(host)
h.mu.Lock()
h.lobbies[lobby.ID] = lobby
h.mu.Unlock()
h.Notifier("lobby_create", lobby)
return lobby
}

func (h *Hub) JoinLobby(client *Client, lobbyID string) (*Lobby, bool) {
h.mu.Lock()
defer h.mu.Unlock()
lobby, ok := h.lobbies[lobbyID]
if !ok || lobby.PlayerCount() >= lobby.MaxPlayer {
return nil, false
}
lobby.AddPlayer(client)
h.Notifier("lobby_join", map[string]interface{}{"lobby": lobby, "player": client})
return lobby, true
}

func (h *Hub) GetLobbies(platform string) []*Lobby {
h.mu.RLock()
defer h.mu.RUnlock()
var result []*Lobby
for _, l := range h.lobbies {
if platform == "" || l.Platform == platform {
result = append(result, l)
}
}
return result
}

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
