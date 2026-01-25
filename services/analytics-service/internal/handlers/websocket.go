package handlers

import (
	"encoding/json"
	"net/http"
	"sync"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"

	"github.com/linkpulse/analytics-service/internal/domain"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type WebSocketHub struct {
	clients    map[*websocket.Conn]bool
	broadcast  chan *domain.ClickEvent
	register   chan *websocket.Conn
	unregister chan *websocket.Conn
	mu         sync.RWMutex
}

func NewWebSocketHub() *WebSocketHub {
	return &WebSocketHub{
		clients:    make(map[*websocket.Conn]bool),
		broadcast:  make(chan *domain.ClickEvent, 100),
		register:   make(chan *websocket.Conn),
		unregister: make(chan *websocket.Conn),
	}
}

func (h *WebSocketHub) Run() {
	for {
		select {
		case conn := <-h.register:
			h.mu.Lock()
			h.clients[conn] = true
			h.mu.Unlock()

		case conn := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[conn]; ok {
				delete(h.clients, conn)
				conn.Close()
			}
			h.mu.Unlock()

		case event := <-h.broadcast:
			h.mu.RLock()
			data, _ := json.Marshal(event)
			for conn := range h.clients {
				err := conn.WriteMessage(websocket.TextMessage, data)
				if err != nil {
					conn.Close()
					delete(h.clients, conn)
				}
			}
			h.mu.RUnlock()
		}
	}
}

func (h *WebSocketHub) Broadcast(event *domain.ClickEvent) {
	select {
	case h.broadcast <- event:
	default:
	}
}

func wsHandler(hub *WebSocketHub) gin.HandlerFunc {
	return func(c *gin.Context) {
		conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
		if err != nil {
			return
		}

		hub.register <- conn

		defer func() {
			hub.unregister <- conn
		}()

		for {
			_, _, err := conn.ReadMessage()
			if err != nil {
				break
			}
		}
	}
}
