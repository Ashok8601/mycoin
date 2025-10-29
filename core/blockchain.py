import hashlib
import json
from time import time
from urllib.parse import urlparse
import requests 
from typing import Set, Dict, Any, List, Optional
# pycryptodome से SHA256 का उपयोग (इंस्टॉल करना आवश्यक है)
from Crypto.Hash import SHA256 

# स्थानीय मॉड्यूल से इंपोर्ट करें (Local Module Imports)
from .cryptos import verify_signature 
from wallet.balance_manager import BalanceManager, has_sufficient_funds 
from utils.data_storage import save_blockchain, load_blockchain, load_blockchain_data 
# P2P नेटवर्क मॉड्यूल
from .p2p_network import broadcast_transaction, broadcast_new_block 


# ----------------------------------------------------
# ग्लोबल सेटिंग्स (Global Constants)
# ----------------------------------------------------

BLOCK_GENERATION_INTERVAL = 600       
DIFFICULTY_ADJUSTMENT_INTERVAL = 2016 
INITIAL_REWARD = 50                   
HALVING_INTERVAL = 210000             

# ----------------------------------------------------
# 1. ब्लॉकचेन क्लास (The Main Engine)
# ----------------------------------------------------

class Blockchain:
    def __init__(self, node_address: str):
        # 1. डेटा लोड करने का प्रयास करें (Persistence)
        loaded_data = load_blockchain()

        if loaded_data:
            self.chain: List[Dict[str, Any]] = loaded_data['chain']
            self.difficulty: int = loaded_data['difficulty']
            self.nodes: Set[str] = loaded_data['nodes']
            self.current_transactions: List[Dict[str, Any]] = []
            self.node_address: str = node_address
            
            print(f"Loaded Chain: {len(self.chain)} blocks, Difficulty: {self.difficulty}")
        else:
            # 2. यदि लोड नहीं होता है, तो जेनेसिस ब्लॉक से शुरू करें
            self.chain = []              
            self.current_transactions = [] 
            self.nodes = set()           
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
    def new_block(self, proof: int, previous_hash: str, miner_address: str) -> Dict[str, Any]:
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
            
        # 3. P2P प्रसारण
        broadcast_new_block(self, block)
            
        return block

    # ------------------------------------------------
    # B. ट्रांजैक्शन जोड़ना (सिग्नेचर, बैलेंस चेक और प्रसारण के साथ)
    # ------------------------------------------------
    def new_transaction(self, sender: str, recipient: str, amount: float, signature: str) -> Tuple[Optional[int], str]:
        """ मेमोरी पूल में एक नया ट्रांजैक्शन जोड़ता है और नेटवर्क पर प्रसारित करता है। """
        
        if sender == "SYSTEM_COINBASE":
            return False, "Error: Cannot manually create a SYSTEM_COINBASE transaction."
        
        # 1. सुरक्षा जाँच
        is_valid_sig = verify_signature(sender, signature, sender, recipient, amount)
        if not is_valid_sig:
            return False, "Error: Invalid digital signature. Transaction rejected."
        
        # 2. बैलेंस जाँच 
        if not has_sufficient_funds(self.balance_manager, sender, amount):
            return False, "Error: Insufficient funds. Transaction rejected."

        # 3. ट्रांजैक्शन को पूल में जोड़ें
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'signature': signature 
        }
        
        self.current_transactions.append(transaction)
        
        # 4. P2P प्रसारण
        broadcast_transaction(self, transaction)
        
        return self.last_block['index'] + 1, "Transaction added to pool"

    # ------------------------------------------------
    # C. हैशिंग और PoW लॉजिक
    # ------------------------------------------------
    @staticmethod
    def hash(block: Dict[str, Any]) -> str:
        """किसी ब्लॉक का SHA-256 हैश बनाता है"""
        block_copy = block.copy()
        if 'transactions' in block_copy:
             block_copy['transactions'] = sorted(block_copy['transactions'], key=lambda x: json.dumps(x, sort_keys=True))
        
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        return SHA256.new(block_string).hexdigest()

    def proof_of_work(self, last_block: Dict[str, Any]) -> int:
        last_hash = self.hash(last_block)
        proof = 0
        while not self.valid_proof(last_hash, proof, self.difficulty):
            proof += 1
        
        return proof

    @staticmethod
    def valid_proof(last_hash: str, proof: int, difficulty: int) -> bool:
        guess = f'{last_hash}{proof}'.encode()
        guess_hash = SHA256.new(guess).hexdigest()
        target_prefix = '0' * difficulty
        return guess_hash.startswith(target_prefix)
        
    # ------------------------------------------------
    # D. PoW कठिनाई और रिवॉर्ड
    # ------------------------------------------------
    def adjust_difficulty(self):
        if len(self.chain) < DIFFICULTY_ADJUSTMENT_INTERVAL:
            return

        first_block = self.chain[-DIFFICULTY_ADJUSTMENT_INTERVAL]
        last_block = self.chain[-1]
        
        time_taken = last_block['timestamp'] - first_block['timestamp']
        expected_time = DIFFICULTY_ADJUSTMENT_INTERVAL * BLOCK_GENERATION_INTERVAL

        if time_taken < expected_time * 0.75: 
            self.difficulty += 1
        elif time_taken > expected_time * 1.25:
            if self.difficulty > 1:
                self.difficulty -= 1

    @staticmethod
    def get_mining_reward(block_index: int) -> float:
        halving_count = block_index // HALVING_INTERVAL
        reward = INITIAL_REWARD / (2 ** halving_count)
        
        if reward < 0.00000001: 
            return 0
        
        return reward

    # ------------------------------------------------
    # E. चेन की वैधता जाँच
    # ------------------------------------------------
    def is_valid_chain(self, chain: List[Dict[str, Any]]) -> Tuple[bool, str]:
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            
            # 1. हैश की जाँच
            if block['previous_hash'] != self.hash(last_block):
                return False, f"Block {block['index']} has invalid previous hash"

            # 2. PoW की जाँच
            # पिछली कठिनाई प्राप्त करें, या 4 का उपयोग करें यदि उपलब्ध न हो
            prev_difficulty = last_block.get('difficulty', 4) 
            if not self.valid_proof(block['previous_hash'], block['proof'], prev_difficulty):
                return False, f"Block {block['index']} has invalid proof"

            last_block = block
            current_index += 1

        return True, "Chain is Valid"

    # ------------------------------------------------
    # G. विकेन्द्रीकृत सर्वसम्मति (Consensus / Conflict Resolution)
    # ------------------------------------------------
    def register_node(self, address: str):
        parsed_url = urlparse(address)
        # urlparse.netloc केवल 'hostname:port' देता है
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # यदि केवल 'example.com' जैसा कुछ दिया गया है
             self.nodes.add(parsed_url.path)
             
    def resolve_conflicts(self) -> bool:
        """
        सर्वसम्मति एल्गोरिथम: सबसे लंबी और वैध चेन को स्वीकार करता है।
        """
        neighbours = self.nodes
        new_chain: Optional[List[Dict[str, Any]]] = None
        max_length = len(self.chain)
        
        for node in neighbours:
            # Render URLs के लिए 'https' का उपयोग करें
            url = f'https://{node}/chain' if 'http' not in node and 'https' not in node else f'{node}/chain'
            
            try:
                response = requests.get(url, timeout=5) 
            except requests.exceptions.RequestException:
                continue

            if response.status_code == 200:
                data = response.json()
                length = data['length']
                chain = data['chain']

                if length > max_length:
                    is_valid, _ = self.is_valid_chain(chain)
                    if is_valid:
                        max_length = length
                        new_chain = chain

        if new_chain:
            # 1. वर्तमान ट्रांजैक्शन पूल को सहेजें
            old_transactions = self.current_transactions
            
            # 2. चेन बदलें
            self.chain = new_chain
            self.balance_manager.recalculate_balances() 
            
            # 3. मेमोरी पूल क्लीनअप
            new_chain_txs = set()
            for block in self.chain:
                for tx in block['transactions']:
                    if tx['sender'] != "SYSTEM_COINBASE":
                        new_chain_txs.add(json.dumps(tx, sort_keys=True))
                        
            self.current_transactions = []
            for tx in old_transactions:
                tx_string = json.dumps(tx, sort_keys=True)
                if tx_string not in new_chain_txs:
                    self.current_transactions.append(tx)
            
            # 4. डेटा को डिस्क पर सेव करें
            save_blockchain(self.chain, self.difficulty, self.nodes)
            
            return True 

        return False
        
    @property
    def last_block(self) -> Dict[str, Any]:
        return self.chain[-1]
