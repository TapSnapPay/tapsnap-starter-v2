import SwiftUI

struct ReceiptView: View {
    let tx: Transaction?

    var body: some View {
        VStack(spacing: 16) {
            if let tx = tx {
                Image(systemName: "checkmark.circle.fill").font(.system(size: 60))
                Text("Payment successful")
                    .font(.title3).fontWeight(.semibold)
                Text("Amount: $\(String(format: "%.2f", Double(tx.amount_cents)/100))")
                Text("Ref: \(tx.psp_reference ?? "-")")
            } else {
                Text("No transaction")
            }
            Spacer()
        }
        .padding()
        .navigationTitle("Receipt")
    }
}
