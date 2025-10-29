// static/app.js

// Flask Node का पता, पोर्ट 5000 पर मानकर
const API_BASE_URL = window.location.origin;

// ----------------------------------------
// 1. माइनिंग
// ----------------------------------------
function mineBlock() {
    document.getElementById('mine-output').textContent = 'Mining... Please wait.';
    fetch(`${API_BASE_URL}/mine`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('mine-output').textContent = 
                `🎉 Success: ${data.message}\n` +
                `Index: ${data.index}\n` +
                `Reward: ${data.reward} MyCoin`;
            console.log('Mine Success:', data);
        })
        .catch(error => {
            document.getElementById('mine-output').textContent = `❌ Error: Could not connect to API or request failed.`;
            console.error('Mine Error:', error);
        });
}

// ----------------------------------------
// 2. ट्रांजैक्शन भेजें (Mock Signature के साथ)
// ----------------------------------------
function sendTransaction() {
    const sender = document.getElementById('sender-pubkey').value;
    const recipient = document.getElementById('recipient-address').value;
    const amount = parseFloat(document.getElementById('amount').value);
    
    if (!sender || !recipient || isNaN(amount) || amount <= 0) {
        document.getElementById('tx-output').textContent = '❌ Error: सभी फ़ील्ड सही से भरें।';
        return;
    }

    // WARNING: यहाँ हम वॉलेट CLI से Private Key के उपयोग की नकल करने के लिए 
    // एक अस्थायी/mock signature भेज रहे हैं। 
    const mock_signature = 'MOCK_WEB_UI_SIG_' + new Date().getTime(); 

    const transactionData = {
        sender: sender,
        recipient: recipient,
        amount: amount,
        signature: mock_signature 
    };

    fetch(`${API_BASE_URL}/transactions/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(transactionData)
    })
    .then(response => response.json())
    .then(data => {
        // HTTP 406 (निकास त्रुटि) को संभालने के लिए
        if (data.message && data.message.includes("Error")) {
             document.getElementById('tx-output').textContent = `❌ Rejection: ${data.message}`;
        } else {
             document.getElementById('tx-output').textContent = `✅ Success: ${data.message}`;
        }
    })
    .catch(error => {
        document.getElementById('tx-output').textContent = `❌ Error: Could not connect to API or request failed.`;
        console.error('TX Error:', error);
    });
}

// ----------------------------------------
// 3. बैलेंस चेक
// ----------------------------------------
function checkBalance() {
    const address = document.getElementById('balance-address').value;
    if (!address) {
        document.getElementById('balance-output').textContent = '❌ Error: बैलेंस चेक करने के लिए पता भरें।';
        return;
    }
    
    document.getElementById('balance-output').textContent = 'Checking Balance...';
    fetch(`${API_BASE_URL}/balance/${address}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('balance-output').textContent = 
                `✅ Address: ${data.address}\n` +
                `Balance: ${data.balance} MyCoin`;
        })
        .catch(error => {
            document.getElementById('balance-output').textContent = `❌ Error: Could not retrieve balance.`;
            console.error('Balance Error:', error);
        });
}


// ----------------------------------------
// 4. पूरी चेन देखें
// ----------------------------------------
function viewChain() {
    document.getElementById('chain-output').textContent = 'Fetching Chain...';
    fetch(`${API_BASE_URL}/chain`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('chain-output').textContent = 
                `Chain Length: ${data.length}\n` +
                `Difficulty: ${data.difficulty}\n\n` +
                "--- Blocks ---\n" +
                JSON.stringify(data.chain, null, 2);
        })
        .catch(error => {
            document.getElementById('chain-output').textContent = `❌ Error: Could not retrieve chain data.`;
            console.error('Chain Error:', error);
        });
}

// पेज लोड होने पर Node ID को ट्रांजैक्शन इनपुट में प्री-फिल करें
document.addEventListener('DOMContentLoaded', () => {
    const nodeId = document.getElementById('node-address').textContent;
    document.getElementById('sender-pubkey').value = nodeId;
    document.getElementById('balance-address').value = nodeId;
});
