//
//  IPHelper.swift
//  ARKitStreamer
//
//  Created by Pepijn Kooijmans on 08/03/2025.
//

import Foundation
import Network

func getWiFiAddress() -> String {
    var address: String = "Not Available"
    var ifaddr: UnsafeMutablePointer<ifaddrs>?
    if getifaddrs(&ifaddr) == 0 {
        var pointer = ifaddr
        while pointer != nil {
            guard let interface = pointer?.pointee else { return address }
            let addrFamily = interface.ifa_addr.pointee.sa_family
            if addrFamily == UInt8(AF_INET) {
                if let name = String(validatingUTF8: interface.ifa_name), name == "en0" {
                    var addr = interface.ifa_addr.pointee
                    let buffer = UnsafeMutablePointer<Int8>.allocate(capacity: Int(NI_MAXHOST))
                    if getnameinfo(&addr, socklen_t(addr.sa_len), buffer, socklen_t(NI_MAXHOST), nil, socklen_t(0), NI_NUMERICHOST) == 0 {
                        address = String(cString: buffer)
                    }
                    buffer.deallocate()
                }
            }
            pointer = interface.ifa_next
        }
        freeifaddrs(ifaddr)
    }
    return address
}
