#!/bin/bash
# start_nodes.sh: Starts the MyCoin network for testing.

# सुनिश्चित करें कि हम प्रोजेक्ट रूट में हैं
cd "$(dirname "$0")"

# 1. इंस्टॉलेशन
echo "1. Installing required Python libraries..."
pip install -r requirements.txt

# 2. Node A (Port 5000) को बैकग्राउंड में शुरू करें
echo "2. Starting Node A on port 5000 (Genesis Node)..."
# 'nohup' और '&' का उपयोग इसे पृष्ठभूमि में चलाने के लिए होता है।
nohup python blockchain_app.py --port 5000 > node_a.log 2>&1 &
echo "Node A started. Check node_a.log for output."

# 3. कुछ सेकंड रुकें ताकि Node A शुरू हो जाए
sleep 5

# 4. Node B (Port 5001) को Node A से कनेक्ट करके शुरू करें
echo "3. Starting Node B on port 5001 and connecting to Node A..."
nohup python blockchain_app.py --port 5001 --connect http://127.0.0.1:5000 > node_b.log 2>&1 &
echo "Node B started. Check node_b.log for output."

# 5. वॉलेट CLI शुरू करें ताकि यूज़र तुरंत इंटरैक्ट कर सकें
echo "4. Launching Wallet CLI for transactions and balance checks."
echo "---------------------------------------------------------"

python wallet/wallet_cli.py

# 6. जब CLI बंद हो जाए, तो बैकग्राउंड प्रोसेस को मार दें
echo "Stopping background nodes..."
killall python

echo "MyCoin network shutdown complete."
