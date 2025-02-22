import Foundation
import Combine

@MainActor
class WebSocketClient: ObservableObject {
    @Published var streamingToken: String = ""
    @Published var isStreaming: Bool = false

    private var webSocketTask: URLSessionWebSocketTask?
    private let baseURL: String

    init(baseURL: String = "ws://localhost:8000") {
        self.baseURL = baseURL
    }

    func connect() {
        guard let url = URL(string: "\(baseURL)/ws/chat") else { return }
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        receiveMessages()
    }

    func disconnect() {
        webSocketTask?.cancel(with: .normalClosure, reason: nil)
        webSocketTask = nil
    }

    func sendMessage(_ text: String, sessionId: String) {
        let payload: [String: String] = ["message": text, "session_id": sessionId]
        guard let data = try? JSONEncoder().encode(payload),
              let json = String(data: data, encoding: .utf8) else { return }

        isStreaming = true
        streamingToken = ""
        webSocketTask?.send(.string(json)) { _ in }
    }

    private func receiveMessages() {
        webSocketTask?.receive { [weak self] result in
            Task { @MainActor in
                switch result {
                case .success(let message):
                    if case .string(let text) = message,
                       let data = text.data(using: .utf8),
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        let type = json["type"] as? String
                        if type == "token", let delta = json["delta"] as? String {
                            self?.streamingToken += delta
                        } else if type == "done" {
                            self?.isStreaming = false
                        }
                    }
                    self?.receiveMessages()
                case .failure:
                    self?.isStreaming = false
                }
            }
        }
    }
}
