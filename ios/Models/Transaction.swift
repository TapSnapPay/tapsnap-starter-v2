import Foundation

struct Transaction: Identifiable, Codable {
    let id: Int
    let merchant_id: Int
    let amount_cents: Int
    let currency: String
    let status: String
    let psp_reference: String?
    let created_at: Date
}

struct NewTransactionRequest: Codable {
    let merchant_id: Int
    let amount_cents: Int
    let currency: String
}
