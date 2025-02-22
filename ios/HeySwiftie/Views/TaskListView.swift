import SwiftUI

struct TaskItem: Codable, Identifiable {
    let id: String
    let title: String
    let description: String
    let priority: String
    let done: Bool
    let dueDate: String?

    enum CodingKeys: String, CodingKey {
        case id, title, description, priority, done
        case dueDate = "due_date"
    }
}

@MainActor
class TaskListViewModel: ObservableObject {
    @Published var tasks: [TaskItem] = []
    @Published var newTaskText: String = ""

    let serverURL: String

    init(serverURL: String = "http://localhost:8000") {
        self.serverURL = serverURL
    }

    func loadTasks() async {
        guard let url = URL(string: "\(serverURL)/api/tasks/") else { return }
        if let (data, _) = try? await URLSession.shared.data(from: url),
           let decoded = try? JSONDecoder().decode([TaskItem].self, from: data) {
            tasks = decoded
        }
    }

    func addTask() async {
        guard !newTaskText.isEmpty,
              let url = URL(string: "\(serverURL)/api/tasks/") else { return }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["title": newTaskText, "natural_language": true] as [String: Any]
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)

        if let _ = try? await URLSession.shared.data(for: req) {
            newTaskText = ""
            await loadTasks()
        }
    }

    func completeTask(_ id: String) async {
        guard let url = URL(string: "\(serverURL)/api/tasks/\(id)/complete") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "PATCH"
        if let _ = try? await URLSession.shared.data(for: req) {
            await loadTasks()
        }
    }
}

struct TaskListView: View {
    @StateObject private var vm = TaskListViewModel()

    var body: some View {
        NavigationStack {
            List {
                HStack {
                    TextField("Add task (natural language)...", text: $vm.newTaskText)
                    Button("Add") { Task { await vm.addTask() } }
                        .buttonStyle(.borderedProminent)
                        .tint(.purple)
                }

                ForEach(vm.tasks) { task in
                    HStack {
                        Image(systemName: task.done ? "checkmark.circle.fill" : "circle")
                            .foregroundColor(task.done ? .green : .secondary)
                            .onTapGesture { Task { await vm.completeTask(task.id) } }

                        VStack(alignment: .leading) {
                            Text(task.title)
                            if let due = task.dueDate {
                                Text("Due: \(due)").font(.caption).foregroundStyle(.secondary)
                            }
                        }

                        Spacer()

                        priorityBadge(task.priority)
                    }
                }
            }
            .navigationTitle("Tasks")
            .task { await vm.loadTasks() }
        }
    }

    @ViewBuilder
    func priorityBadge(_ priority: String) -> some View {
        let color: Color = switch priority {
            case "urgent": .red
            case "high": .orange
            case "medium": .blue
            default: .gray
        }
        Text(priority)
            .font(.caption2)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(color.opacity(0.15))
            .foregroundColor(color)
            .clipShape(Capsule())
    }
}
