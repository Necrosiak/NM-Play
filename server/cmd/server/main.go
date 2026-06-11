package main

import (
"log"
"os"
"os/signal"
"syscall"

"github.com/networkmemories/nm-play-server/internal/api"
"github.com/networkmemories/nm-play-server/internal/relay"
)

func main() {
log.Println("NM-Play Server starting...")

hub := relay.NewHub()
go hub.Run()

slp := relay.NewSLPRelay(":11451", hub)
go slp.Run()

l2 := relay.NewL2Relay(":11452", hub)
go l2.Run()

psp := relay.NewPSPRelay(":27312", hub)
go psp.Run()

authURL := os.Getenv("NM_AUTH_URL")
if authURL == "" {
authURL = "https://network-memories.com"
}
srv := api.NewServer(":8080", hub, authURL)
go srv.Run()

log.Println("NM-Play Server running:")
log.Println("  Switch SLP  : :11451 UDP")
log.Println("  L2 Tunnel   : :11452 UDP")
log.Println("  PSP Adhoc   : :27312 TCP")
log.Println("  API+WS      : :8080  HTTP")

sig := make(chan os.Signal, 1)
signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
<-sig
log.Println("NM-Play Server shutting down...")
}
