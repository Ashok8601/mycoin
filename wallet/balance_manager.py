import json

# ----------------------------------------------------
# 1. बैलेंस मैनेजर क्लास
# ----------------------------------------------------

class BalanceManager:
    """
    ब्लॉकचेन में हर पते के बैलेंस को ट्रैक करता है
    """
    def __init__(self, blockchain_instance):
        self.blockchain = blockchain_instance
        self.balances = {}  # {address: amount} के रूप में बैलेंस स्टोर करें

    def _update_balances_from_block(self, block):
        """
        एक ब्लॉक के सभी ट्रांजैक्शन को प्रोसेस करके बैलेंस अपडेट करता है।
        """
        for tx in block['transactions']:
            sender = tx['sender']
            recipient = tx['recipient']
            amount = tx['amount']
            
            # सुनिश्चित करें कि बैलेंस डिक्शनरी में पता मौजूद है
            if sender not in self.balances:
                self.balances[sender] = 0.0
            if recipient not in self.balances:
                self.balances[recipient] = 0.0

            # 1. भेजने वाले का बैलेंस घटाएँ (Coinbase को छोड़कर)
            if sender != "SYSTEM_COINBASE":
                self.balances[sender] -= amount
                # सुनिश्चित करें कि बैलेंस ऋणात्मक (negative) न हो जाए (यह केवल सुरक्षा के लिए है, 
                # new_transaction में जाँच होनी चाहिए)
                if self.balances[sender] < 0:
                    self.balances[sender] = 0.0 # यहाँ कोई गंभीर त्रुटि इंगित होती है

            # 2. प्राप्तकर्ता का बैलेंस बढ़ाएँ
            self.balances[recipient] += amount

    def recalculate_balances(self):
        """
        चेन के जेनेसिस ब्लॉक से शुरू करके सभी बैलेंस की गणना करता है।
        यह कंसेंसस के बाद या नोड शुरू होने पर चलाया जाता है।
        """
        self.balances = {} # बैलेंस को रीसेट करें
        
        # चेन के हर ब्लॉक को क्रम से प्रोसेस करें
        for block in self.blockchain.chain:
            self._update_balances_from_block(block)
            
        return self.balances

    def get_balance(self, address):
        """
        किसी दिए गए पते (address) का वर्तमान बैलेंस रिटर्न करता है।
        अगर पता मौजूद नहीं है, तो 0.0 रिटर्न करता है।
        """
        # यदि बैलेंस पहले ही गणना किया गया है, तो इसे सीधे रिटर्न करें
        return self.balances.get(address, 0.0)

# ----------------------------------------------------
# 2. ट्रांजैक्शन के लिए जाँच फ़ंक्शन
# ----------------------------------------------------

def has_sufficient_funds(balance_manager, sender_address, amount):
    """
    जाँच करता है कि भेजने वाले के पास आवश्यक राशि है या नहीं।
    """
    current_balance = balance_manager.get_balance(sender_address)
    
    # यदि भेजने वाले का वर्तमान बैलेंस ट्रांजैक्शन राशि से बड़ा या बराबर है
    if current_balance >= amount:
        return True
    else:
        return False