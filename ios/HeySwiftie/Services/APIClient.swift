import Foundation

struct ChatResponse: Codable {
    let reply: String
    let sessionId: String

    enum CodingKeys: String, CodingKey {
        case reply
        case sessionId = "session_id"
    }
}

struct TranscriptionResponse: Codable {
    let text: String
    let language: String
    let confidence: Double
}

class APIClient: ObservableObject {
    private let baseURL: String
    private let session = URLSession.shared

    init(baseURL: String = "http://localhost:8000") {
        self.baseURL = baseURL
    }

    func sendMessage(_ message: String, sessionId: String) async throws -> ChatResponse {
        guard let url = URL(string: "\(baseURL)/api/chat/") else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: String] = ["message": message, "session_id": sessionId]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        return try JSONDecoder().decode(ChatResponse.self, from: data)
    }

    func transcribe(audioData: Data) async throws -> TranscriptionResponse {
        guard let url = URL(string: "\(baseURL)/api/voice/transcribe") else {
            throw URLError(.badURL)
        }

        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio\"; filename=\"voice.wav\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, _) = try await session.data(for: request)
        return try JSONDecoder().decode(TranscriptionResponse.self, from: data)
    }
}
