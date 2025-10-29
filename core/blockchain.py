import hashlib
import json
from time import time
from urllib.parse import urlparse
import requests 
from typing import Set

# pycryptodome से SHA256 का उपयोग (इंस्टॉल करना आवश्यक है)
from Crypto.Hash import SHA256 

# स्थानीय मॉड्यूल से इंपोर्ट करें (Local Module Imports)
from .cryptos import verify_signature 
from wallet.balance_manager import BalanceManager, has_sufficient_funds 
from utils.data_storage import save_blockchain, load_blockchain, load_blockchain_data # load_blockchain_data जोड़ा गया
# नया इंपोर्ट: P2P नेटवर्क मॉड्यूल
from .p2p_network import broadcast_transaction, broadcast_new_block 


# ----------------------------------------------------
# ग्लोबल सेटिंग्स (Global Constants)
# ----------------------------------------------------

BLOCK_GENERATION_INTERVAL = 600       # 10 मिनट प्रति ब्लॉक (सेकंड में)
DIFFICULTY_ADJUSTMENT_INTERVAL = 2016 # हर 2016 ब्लॉक के बाद कठिनाई समायोजित करें
INITIAL_REWARD = 50                   # हाल्विंग के लिए शुरुआती रिवॉर्ड
HALVING_INTERVAL = 210000             # हर 210,000 ब्लॉक के बाद रिवॉर्ड आधा

# ----------------------------------------------------
# 1. ब्लॉकचेन क्लास (The Main Engine)
# ----------------------------------------------------

class Blockchain:
    # (अन्य __init__ लॉजिक अपरिवर्तित)
    def __init__(self, node_address):
        # 1. डेटा लोड करने का प्रयास करें (Persistence)
        loaded_data = load_blockchain()

        if loaded_data:
            self.chain = loaded_data['chain']
            self.difficulty = loaded_data['difficulty']
            self.nodes = loaded_data['nodes']
            self.current_transactions = []
            self.node_address = node_address
            
            print(f"Loaded Chain: {len(self.chain)} blocks, Difficulty: {self.difficulty}")
        else:
            # 2. यदि लोड नहीं होता है, तो जेनेसिस ब्लॉक से शुरू करें
            self.chain = []              
            self.current_transactions = [] 
            self.nodes: Set[str] = set()           
            self.node_address = node_address 
            self.difficulty = 4          

            if not self.chain:
                self.new_block(proof=100, previous_hash='1', miner_address=node_address)

        # बैलेंस मैनेजर को यहाँ शुरू करें
        self.balance_manager = BalanceManager(self) 
        self.balance_manager.recalculate_balances() 


    # ------------------------------------------------
    # A. नया ब्लॉक बनाना और जोड़ना
    # ------------------------------------------------
    def new_block(self, proof, previous_hash, miner_address):
        """
        एक नया ब्लॉक बनाता है, रिवॉर्ड जोड़ता है, चेन में जोड़ता है, डिस्क पर सेव करता है, 
        और नेटवर्क पर प्रसारित करता है।
        """
        
        reward_amount = self.get_mining_reward(len(self.chain) + 1)
        
        # Coinbase Transaction
        coinbase_tx = {
            'sender': "SYSTEM_COINBASE",
            'recipient': miner_address,
            'amount': reward_amount,
            'signature': 'GENESIS_SIG'
        }
        
        transactions_to_include = [coinbase_tx] + self.current_transactions

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': transactions_to_include,
            'proof': proof,
            'previous_hash': previous_hash,
            'miner': miner_address,
            'difficulty': self.difficulty, 
        }

        self.current_transactions = []
        self.chain.append(block)
        
        # 1. डेटा सेव करें
        save_blockchain(self.chain, self.difficulty, self.nodes)
        
        # 2. कठिनाई समायोजित करें
        if block['index'] % DIFFICULTY_ADJUSTMENT_INTERVAL == 0:
            self.adjust_difficulty()
            
        # 3. P2P प्रसारण (MOST IMPORTANT NEW STEP)
        broadcast_new_block(self, block) # यह अब अपडेटेड फंक्शन को कॉल करेगा
            
        return block

    # (अन्य फंक्शन्स अपरिवर्तित)
    
    # ------------------------------------------------
    # F. P2P प्रसारण फ़ंक्शन (core/blockchain.py से हटा दिया गया, अब p2p_network.py में)
    # ------------------------------------------------
    # नोट: चूंकि आपने broadcast_new_block को 'p2p_network' से आयात किया है, 
    # हम मानते हैं कि वास्तविक P2P लॉजिक वहाँ है।
    
    # ------------------------------------------------
    # G. विकेन्द्रीकृत सर्वसम्मति (Consensus / Conflict Resolution)
    # ------------------------------------------------
    def register_node(self, address):
        parsed_url = urlparse(address)
        # urlparse.netloc केवल 'hostname:port' देता है
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # यदि केवल 'example.com' जैसा कुछ दिया गया है
             self.nodes.add(parsed_url.path)
             
    # (resolve_conflicts और अन्य फंक्शन्स अपरिवर्तित)
    
    # ... बाकी सभी फंक्शन्स अपरिवर्तित हैं ...
