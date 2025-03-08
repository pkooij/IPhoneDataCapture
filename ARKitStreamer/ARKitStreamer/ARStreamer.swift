//
//  ARStreamer.swift
//  ARKitStreamer
//
//  Created by Pepijn Kooijmans on 08/03/2025.
//

import Foundation
import ARKit
import Network
import UIKit
import CoreImage
import SwiftUI

class ARStreamer: NSObject, ARSessionDelegate, ObservableObject {
    
    private var listener: NWListener?
    private var connection: NWConnection?
    
    @Published var isConnected: Bool = false

    func startServer(port: UInt16 = 5555) {
        do {
            listener = try NWListener(using: .tcp, on: NWEndpoint.Port(rawValue: port)!)
            
            listener?.stateUpdateHandler = { state in
                print("Listener state: \(state)")
            }
            
            listener?.newConnectionHandler = { [weak self] newConnection in
                self?.setupConnection(newConnection)
            }
            
            listener?.start(queue: .global())
            print("Listening on port \(port)...")
        } catch {
            print("Unable to start listener: \(error)")
        }
    }
    
    private func setupConnection(_ newConnection: NWConnection) {
        connection = newConnection
        connection?.stateUpdateHandler = { [weak self] state in
            DispatchQueue.main.async {
                self?.isConnected = (state == .ready)
            }
            print("Connection state: \(state)")
        }
        connection?.start(queue: .global())
        print("Client connected: \(newConnection.endpoint)")
    }
    
    // ARSessionDelegate callback without frame rate throttling:
    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        sendFrame(frame)
    }
    
    private func sendFrame(_ frame: ARFrame) {
        guard let connection = connection else { return }

        // ------------------
        // 1) Pose transform
        // ------------------
        let transform = frame.camera.transform
        let transformArray: [Float] = [
            transform.columns.0.x, transform.columns.0.y, transform.columns.0.z, transform.columns.0.w,
            transform.columns.1.x, transform.columns.1.y, transform.columns.1.z, transform.columns.1.w,
            transform.columns.2.x, transform.columns.2.y, transform.columns.2.z, transform.columns.2.w,
            transform.columns.3.x, transform.columns.3.y, transform.columns.3.z, transform.columns.3.w
        ]
        
        // ------------------
        // 2) Intrinsics 3x3
        // ------------------
        let intrinsics = frame.camera.intrinsics
        let intrinsicsArray: [Float] = [
            intrinsics.columns.0.x, intrinsics.columns.0.y, intrinsics.columns.0.z,
            intrinsics.columns.1.x, intrinsics.columns.1.y, intrinsics.columns.1.z,
            intrinsics.columns.2.x, intrinsics.columns.2.y, intrinsics.columns.2.z
        ]
        
        // -----------
        // 3) RGB image
        // -----------
        let ciImage = CIImage(cvPixelBuffer: frame.capturedImage)
        let context = CIContext()
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else { return }
        let uiImage = UIImage(cgImage: cgImage)
        guard let jpgData = uiImage.jpegData(compressionQuality: 0.5) else { return }

        // Build dictionary
        var frameDict: [String: Any] = [
            "transform": transformArray,
            "intrinsics": intrinsicsArray,
            "timestamp": frame.timestamp
        ]

        // -----------
        // 4) Depth map
        // -----------
        var depthData = Data()
        if let sceneDepth = frame.sceneDepth {
            let depthBuffer = sceneDepth.depthMap
            CVPixelBufferLockBaseAddress(depthBuffer, .readOnly)
            let depthWidth = CVPixelBufferGetWidth(depthBuffer)
            let depthHeight = CVPixelBufferGetHeight(depthBuffer)
            let depthPtr = CVPixelBufferGetBaseAddress(depthBuffer)!
            let depthDataSize = CVPixelBufferGetDataSize(depthBuffer)
            
            depthData = Data(bytes: depthPtr, count: depthDataSize)
            CVPixelBufferUnlockBaseAddress(depthBuffer, .readOnly)

            frameDict["depthWidth"] = depthWidth
            frameDict["depthHeight"] = depthHeight
        }

        guard let jsonData = try? JSONSerialization.data(withJSONObject: frameDict) else {
            print("Could not serialize frameDict to JSON!")
            return
        }

        var packet = Data()
        var jsonLength = Int32(jsonData.count)
        var jpegLength = Int32(jpgData.count)
        var depthLength = Int32(depthData.count)

        packet.append(Data(bytes: &jsonLength, count: 4))
        packet.append(jsonData)
        packet.append(Data(bytes: &jpegLength, count: 4))
        packet.append(jpgData)
        packet.append(Data(bytes: &depthLength, count: 4))
        packet.append(depthData)

        connection.send(content: packet, completion: .contentProcessed { error in
            if let error = error {
                print("Send error: \(error)")
            }
        })
    }
}
