import SwiftUI

@main
struct HeySwiftieApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
    }
}

class AppState: ObservableObject {
    @Published var sessionId: String = UUID().uuidString
    @Published var serverURL: String = "http://localhost:8000"
    @Published var isConnected: Bool = false

    func resetSession() {
        sessionId = UUID().uuidString
    }
}
