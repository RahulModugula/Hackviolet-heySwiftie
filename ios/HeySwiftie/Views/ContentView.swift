import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        TabView {
            ChatView()
                .tabItem {
                    Label("Chat", systemImage: "bubble.left.and.bubble.right")
                }

            MemoryView()
                .tabItem {
                    Label("Memory", systemImage: "brain")
                }

            TaskListView()
                .tabItem {
                    Label("Tasks", systemImage: "checklist")
                }

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
        }
        .accentColor(.purple)
    }
}
