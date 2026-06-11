package api

import (
"encoding/json"
"log"
"sync"

"github.com/gorilla/websocket"
)

type WSMessage struct {
Event string      `json:"event"`
Data  interface{} `json:"data"`
}

type WSHub struct {
clients map[*websocket.Conn]bool
mu      sync.RWMutex
send    chan WSMessage
}

func NewWSHub() *WSHub {
return &WSHub{
clients: make(map[*websocket.Conn]bool),
send:    make(chan WSMessage, 256),
}
}

func (h *WSHub) Run() {
for msg := range h.send {
h.mu.Lock()
data, _ := json.Marshal(msg)
for conn := range h.clients {
if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
conn.Close()
delete(h.clients, conn)
}
}
h.mu.Unlock()
}
}

func (h *WSHub) AddClient(conn *websocket.Conn) {
h.mu.Lock()
h.clients[conn] = true
h.mu.Unlock()
log.Printf("[WS] Client connected, total: %d", len(h.clients))
go func() {
defer func() {
h.mu.Lock()
delete(h.clients, conn)
h.mu.Unlock()
conn.Close()
}()
for {
if _, _, err := conn.ReadMessage(); err != nil {
return
}
}
}()
}

func (h *WSHub) Broadcast(event string, data interface{}) {
select {
case h.send <- WSMessage{Event: event, Data: data}:
default:
}
}
