import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @AppStorage("serverURL") private var serverURL: String = "http://localhost:8000"
    @AppStorage("privacyMode") private var privacyMode: Bool = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Server") {
                    TextField("Server URL", text: $serverURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                }

                Section("Privacy") {
                    Toggle("Privacy Mode (local LLM only)", isOn: $privacyMode)
                    Text("When enabled, all processing stays on-device using Ollama.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Session") {
                    Text("Session ID: \(appState.sessionId)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("New Session", role: .destructive) {
                        appState.resetSession()
                    }
                }

                Section("About") {
                    HStack {
                        Text("heySwiftie")
                        Spacer()
                        Text("v0.5.0").foregroundStyle(.secondary)
                    }
                    HStack {
                        Text("Model")
                        Spacer()
                        Text(privacyMode ? "Local (Ollama)" : "Cloud").foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}
