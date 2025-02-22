import Foundation
import AVFoundation
import Combine

@MainActor
class AudioRecorder: NSObject, ObservableObject {
    @Published var isRecording = false
    @Published var recordedData: Data?

    private var audioRecorder: AVAudioRecorder?
    private var tempURL: URL?

    func startRecording() {
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 16000,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
        ]

        tempURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString + ".wav")

        guard let url = tempURL else { return }

        do {
            try AVAudioSession.sharedInstance().setCategory(.record, mode: .default)
            try AVAudioSession.sharedInstance().setActive(true)
            audioRecorder = try AVAudioRecorder(url: url, settings: settings)
            audioRecorder?.record()
            isRecording = true
        } catch {
            print("Recording failed: \(error)")
        }
    }

    func stopRecording() {
        audioRecorder?.stop()
        isRecording = false
        if let url = tempURL {
            recordedData = try? Data(contentsOf: url)
            try? FileManager.default.removeItem(at: url)
        }
    }
}
