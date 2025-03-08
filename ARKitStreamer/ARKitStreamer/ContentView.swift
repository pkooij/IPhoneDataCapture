//
//  ContentView.swift
//  ARKitStreamer
//
//  Created by Pepijn Kooijmans on 08/03/2025.
//

import SwiftUI
import ARKit

struct ContentView: UIViewRepresentable {
    @StateObject var arStreamer = ARStreamer()

    func makeUIView(context: Context) -> ARSCNView {
        let sceneView = ARSCNView()
        sceneView.session.delegate = arStreamer
        arStreamer.startServer(port: 5555)

        let configuration = ARWorldTrackingConfiguration()
        configuration.planeDetection = .horizontal
        sceneView.session.run(configuration)

        return sceneView
    }

    func updateUIView(_ uiView: ARSCNView, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(arStreamer: arStreamer)
    }

    class Coordinator: NSObject {
        var arStreamer: ARStreamer

        init(arStreamer: ARStreamer) {
            self.arStreamer = arStreamer
        }
    }
}

struct MainView: View {
    @StateObject private var arStreamer = ARStreamer()
    @State private var ipAddress = "Fetching..."

    var body: some View {
        ZStack {
            // AR Camera View
            ContentView(arStreamer: arStreamer)
                .edgesIgnoringSafeArea(.all)

            // Overlay UI (status indicators)
            VStack {
                Spacer().frame(height: 50) // Adjust to move UI down from top notch

                HStack {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("IP Address: \(ipAddress)")
                            .font(.headline)
                            .foregroundColor(.black)
                            .padding(8)
                            .background(Color.white.opacity(0.8))
                            .cornerRadius(8)

                        Text("Connection: \(arStreamer.isConnected ? "✅ Connected" : "❌ Not Connected")")
                            .font(.headline)
                            .foregroundColor(.black)
                            .padding(8)
                            .background(Color.white.opacity(0.8))
                            .cornerRadius(8)
                    }
                    .padding(.leading, 16)

                    Spacer()
                }

                Spacer() // Push everything to top-left corner
            }
        }
        .onAppear {
            ipAddress = getWiFiAddress()
        }
    }
}
