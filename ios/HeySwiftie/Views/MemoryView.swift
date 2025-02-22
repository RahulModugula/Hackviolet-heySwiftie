import SwiftUI

struct MemoryFact: Codable, Identifiable {
    var id: String { "\(subject):\(predicate)" }
    let subject: String
    let predicate: String
    let value: String
    let confidence: Double
}

struct MemoryItem: Codable, Identifiable {
    let id: String
    let type: String
    let content: String
    let importance: Double
    let ageHours: Double

    enum CodingKeys: String, CodingKey {
        case id, type, content, importance
        case ageHours = "age_hours"
    }
}

@MainActor
class MemoryViewModel: ObservableObject {
    @Published var facts: [MemoryFact] = []
    @Published var memories: [MemoryItem] = []
    @Published var recallQuery: String = ""

    let serverURL: String

    init(serverURL: String = "http://localhost:8000") {
        self.serverURL = serverURL
    }

    func loadFacts() async {
        guard let url = URL(string: "\(serverURL)/api/memory/facts") else { return }
        if let (data, _) = try? await URLSession.shared.data(from: url),
           let decoded = try? JSONDecoder().decode([MemoryFact].self, from: data) {
            facts = decoded
        }
    }

    func recall() async {
        guard !recallQuery.isEmpty,
              let url = URL(string: "\(serverURL)/api/memory/recall?q=\(recallQuery.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") else { return }
        if let (data, _) = try? await URLSession.shared.data(from: url),
           let decoded = try? JSONDecoder().decode([MemoryItem].self, from: data) {
            memories = decoded
        }
    }
}

struct MemoryView: View {
    @StateObject private var vm = MemoryViewModel()

    var body: some View {
        NavigationStack {
            List {
                Section("What I know about you") {
                    if vm.facts.isEmpty {
                        Text("No facts stored yet. Start chatting!")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(vm.facts) { fact in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(fact.value).font(.body)
                                Text("\(fact.predicate)").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                }

                Section {
                    HStack {
                        TextField("Search memories...", text: $vm.recallQuery)
                        Button("Recall") { Task { await vm.recall() } }
                            .buttonStyle(.borderedProminent)
                            .tint(.purple)
                    }
                    ForEach(vm.memories) { mem in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(mem.content).font(.caption)
                            HStack {
                                Label(mem.type, systemImage: mem.type == "semantic" ? "brain" : "clock")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(String(format: "%.0fh ago", mem.ageHours))
                                    .font(.caption2).foregroundStyle(.secondary)
                            }
                        }
                    }
                } header: { Text("Memory Recall") }
            }
            .navigationTitle("Memory")
            .task { await vm.loadFacts() }
        }
    }
}
