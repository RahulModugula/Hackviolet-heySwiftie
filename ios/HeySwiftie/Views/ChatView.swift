import SwiftUI

@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [Message] = []
    @Published var inputText: String = ""
    @Published var isLoading: Bool = false
    @Published var streamingReply: String = ""

    private let apiClient: APIClient
    private let wsClient: WebSocketClient
    private let recorder: AudioRecorder

    var sessionId: String

    init(serverURL: String, sessionId: String) {
        self.apiClient = APIClient(baseURL: serverURL)
        self.wsClient = WebSocketClient(baseURL: serverURL.replacingOccurrences(of: "http", with: "ws"))
        self.recorder = AudioRecorder()
        self.sessionId = sessionId
        wsClient.connect()

        // observe streaming tokens
        wsClient.$streamingToken
            .receive(on: RunLoop.main)
            .assign(to: &$streamingReply)

        wsClient.$isStreaming
            .receive(on: RunLoop.main)
            .sink { [weak self] streaming in
                if !streaming, let self, !self.streamingReply.isEmpty {
                    let reply = Message(role: .assistant, content: self.streamingReply)
                    self.messages.append(reply)
                    self.streamingReply = ""
                }
            }
            .store(in: &cancellables)
    }

    private var cancellables = Set<AnyCancellable>()

    func send() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        inputText = ""
        messages.append(Message(role: .user, content: text))
        wsClient.sendMessage(text, sessionId: sessionId)
    }

    func startVoice() {
        recorder.startRecording()
    }

    func stopVoice() {
        recorder.stopRecording()
        guard let data = recorder.recordedData else { return }
        Task {
            do {
                let transcription = try await apiClient.transcribe(audioData: data)
                inputText = transcription.text
            } catch {
                print("Transcription error: \(error)")
            }
        }
    }

    var isRecording: Bool { recorder.isRecording }
}

struct ChatView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel: ChatViewModel

    init() {
        // use a placeholder; will be overridden once environment is available
        _viewModel = StateObject(wrappedValue: ChatViewModel(
            serverURL: "http://localhost:8000",
            sessionId: UUID().uuidString
        ))
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(viewModel.messages) { msg in
                                MessageBubble(message: msg)
                                    .id(msg.id)
                            }
                            if !viewModel.streamingReply.isEmpty {
                                MessageBubble(message: Message(role: .assistant, content: viewModel.streamingReply))
                                    .id("streaming")
                            }
                        }
                        .padding()
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        withAnimation { proxy.scrollTo("streaming") }
                    }
                }

                Divider()
                InputBar(viewModel: viewModel)
            }
            .navigationTitle("Swiftie")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("New") { appState.resetSession() }
                }
            }
        }
    }
}

struct MessageBubble: View {
    let message: Message

    var isUser: Bool { message.role == .user }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 60) }
            Text(message.content)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(isUser ? Color.purple : Color(.secondarySystemBackground))
                .foregroundColor(isUser ? .white : .primary)
                .clipShape(RoundedRectangle(cornerRadius: 18))
            if !isUser { Spacer(minLength: 60) }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }
}

struct InputBar: View {
    @ObservedObject var viewModel: ChatViewModel

    var body: some View {
        HStack(spacing: 10) {
            TextField("Message", text: $viewModel.inputText, axis: .vertical)
                .padding(10)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 20))
                .lineLimit(1...5)
                .onSubmit { viewModel.send() }

            Button {
                if viewModel.isRecording {
                    viewModel.stopVoice()
                } else {
                    viewModel.startVoice()
                }
            } label: {
                Image(systemName: viewModel.isRecording ? "mic.fill" : "mic")
                    .foregroundColor(viewModel.isRecording ? .red : .purple)
                    .font(.title3)
            }

            Button(action: viewModel.send) {
                Image(systemName: "arrow.up.circle.fill")
                    .foregroundColor(viewModel.inputText.isEmpty ? .gray : .purple)
                    .font(.title2)
            }
            .disabled(viewModel.inputText.isEmpty)
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
    }
}
