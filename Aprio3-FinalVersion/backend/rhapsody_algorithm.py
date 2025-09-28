"""
RHAPSODY Algorithm Implementation
Author: Ludjina
Description: Implementation of the RHAPSODY algorithm for ABAC policy mining
"""

import pandas as pd
from mlxtend.frequent_patterns import apriori
from mlxtend.preprocessing import TransactionEncoder
import warnings
warnings.filterwarnings('ignore')

import json


class RhapsodyAlgorithm:
    """
    RHAPSODY Algorithm for ABAC Policy Mining
    
    This class implements the three-stage RHAPSODY algorithm:
    Stage 1: Computing Frequent Rules
    Stage 2: Computing Reliable Rules  
    Stage 3: Removing Redundant Rules
    """
    
    def __init__(self, selected_columns=None):
        self.data = None
        self.selected_columns = selected_columns
        self.working_columns = None
        self.freq_rules = []
        self.rel_rules = []
        self.final_rules = []
        self.nUP = {}
        self.nA = {}
        self.transactions = []
        
    def load_data(self, data_path):
        """Load CSV data from file path"""
        try:
            self.data = pd.read_csv(data_path)
            if self.selected_columns:
                # Verify all selected columns exist
                missing_cols = [col for col in self.selected_columns if col not in self.data.columns]
                if missing_cols:
                    raise ValueError(f"Selected columns not found in data: {missing_cols}")
                self.data = self.data[self.selected_columns]
                self.working_columns = self.selected_columns.copy()
            else:
                self.working_columns = list(self.data.columns)   

            print(f"Loaded {len(self.data)} records with {len(self.data.columns)} columns from {data_path}")
            print(f"Working with columns: {self.working_columns}")  # debug line
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def load_data_from_dataframe(self, df):
        """Load data from pandas DataFrame"""
        self.data = df.copy()
        
        # Filter to selected columns if specified
        if self.selected_columns:
            missing_cols = [col for col in self.selected_columns if col not in self.data.columns]
            if missing_cols:
                raise ValueError(f"Selected columns not found in data: {missing_cols}")
            self.data = self.data[self.selected_columns] 
            self.working_columns = self.selected_columns.copy()
        else:            
            self.working_columns = list(self.data.columns)

        print(f"Loaded {len(self.data)} records with {len(self.data.columns)} columns from DataFrame")
        print(f"Working with columns: {self.working_columns}")  # debug line
        return True
        
    def run_algorithm(self, T, K):
        """
        Run the complete RHAPSODY algorithm
        
        Args:
            T (int): Support threshold
            K (float): Reliability threshold (0-1)
            
        Returns:
            tuple: (final_rules, nUP, nA)
        """
        if self.data is None:
            raise ValueError("No data loaded. Please load data first.")
            
        print(f"Running RHAPSODY with T={T}, K={K}")
        
        print("\n=== STAGE 1: Computing Frequent Rules ===")
        self.freq_rules, self.nUP, self.nA = self._stage1(T)
        
        print("\n=== STAGE 2: Computing Reliable Rules ===")
        self.rel_rules = self._stage2(T, K)
        
        print("\n=== STAGE 3: Removing Redundant Rules ===")
        self.final_rules = self._stage3()
        
        return self.final_rules, self.nUP, self.nA
    
    def _stage1(self, T):
        """
        Stage 1: Compute FreqRules, nU×P, and nA
        """
        # Create atoms for each transaction
        def create_atoms(row):
            atoms = []
            for col in self.working_columns:  
                if pd.notna(row[col]):  # Handle NaN values
                    atoms.append(f"{col}={row[col]}")
            return frozenset(atoms)
    
        self.data['atoms'] = self.data.apply(create_atoms, axis=1)
        self.transactions = list(self.data['atoms'])
        print(f"Created {len(self.transactions)} transactions")
        
        # Encode transactions for frequent itemset mining
        te = TransactionEncoder()
        te_array = te.fit(self.transactions).transform(self.transactions)
        df_encoded = pd.DataFrame(te_array, columns=te.columns_)
        
        # Calculate minimum support
        min_support = T / len(self.transactions)
        print(f"Minimum support: {min_support:.4f} (T={T}, total transactions={len(self.transactions)})")
        
        # Find frequent itemsets
        freq_itemsets = apriori(df_encoded, min_support=min_support, use_colnames=True)
        
        if freq_itemsets.empty:
            print("No frequent itemsets found with the given threshold")
            return [], {}, {}
        
        # Generate frequent rules
        freq_rules = []
        nUP = {}
        
        for _, row in freq_itemsets.iterrows():
            itemset = row['itemsets']
            rule = " ∧ ".join(sorted(itemset))
            freq_rules.append(rule)
            nUP[rule] = int(row['support'] * len(self.transactions))
        
        print(f"Generated {len(freq_rules)} frequent rules")
        
        # Calculate nA (number of attributes)
        nA = {}
        for rule in freq_rules:
            nA[rule] = 0
        
        # Count how many transactions satisfy each rule
        for _, row in self.data.iterrows():
            request_atoms = set()
            for col in self.working_columns:  
                if pd.notna(row[col]):
                    request_atoms.add(f"{col}={row[col]}")
            
            for rule in freq_rules:
                rule_atoms = set(rule.split(" ∧ "))
                if rule_atoms.issubset(request_atoms):
                    nA[rule] += 1
        
        return freq_rules, nUP, nA
    
    def _stage2(self, T, K):
        """
        Stage 2: Compute RelRules (rules with T-reliability ≥ K)
        """
        unrel_rules = set()
        
        # Check all pairs of rules
        for r1 in self.freq_rules:
            for r2 in self.freq_rules:
                if r1 != r2:
                    # Check if r2 proves that RelT(r1) < K
                    if self._proves_unreliability(r1, r2, T, K):
                        unrel_rules.add(r1)
        
        # Compute RelRules = FreqRules \ UnrelRules
        rel_rules = [rule for rule in self.freq_rules if rule not in unrel_rules]
        
        print(f"Unreliable rules: {len(unrel_rules)}")
        print(f"Reliable rules: {len(rel_rules)}")
        
        return rel_rules
    
    def _proves_unreliability(self, r1, r2, T, K):
        """
        Check if r2 proves that RelT(r1) < K
        Conditions:
        (i) r2 is a refinement of r1 (r1 ⊆ r2)
        (ii) |r2_U×P| ≥ T
        (iii) Conf(r2) < K
        """
        r1_atoms = set(r1.split(" ∧ "))
        r2_atoms = set(r2.split(" ∧ "))
        
        # (i) Check if r1 is subset of r2
        if not r1_atoms.issubset(r2_atoms):
            return False
        
        # (ii) Check support threshold
        if self.nUP[r2] < T:
            return False
        
        # (iii) Check confidence threshold
        # Conf(r2) = |r2_U×P| / (|r1_U×P| + |r2_U×P|)
        confidence = self.nUP[r2] / (self.nUP[r1] + self.nUP[r2])
        
        if confidence < K:
            return True
        
        return False
    
    def _stage3(self):
        """
        Stage 3: Remove redundant rules
        """
        subsumed = set()
        
        for r1 in self.rel_rules:
            for r2 in self.rel_rules:
                if r1 != r2:
                    if self._are_equivalent(r1, r2) and self._is_shorter(r2, r1):
                        subsumed.add(r1)
        
        short_rules = [rule for rule in self.rel_rules if rule not in subsumed]
        short_rules = sorted(short_rules, key=lambda x: self.nA[x])
        
        print(f"Subsumed rules: {len(subsumed)}")
        print(f"Final concise rules: {len(short_rules)}")
        
        return short_rules
    
    def _are_equivalent(self, r1, r2):
        """
        Check if two rules are equivalent
        A rule r1 is equivalent to r2 if:
        - nU×P(r1) = nU×P(r2)
        - r1 ∧ r2 is in FreqRules
        """
        if self.nUP[r1] != self.nUP[r2]:
            return False
        
        r1_atoms = set(r1.split(" ∧ "))
        r2_atoms = set(r2.split(" ∧ "))

        # If one rule's conditions are a subset of the other's, they're equivalent
        # when they have the same coverage
        return r1_atoms.issubset(r2_atoms) or r2_atoms.issubset(r1_atoms)

        
    def _is_shorter(self, r1, r2):
        """
        Check if rule r1 is shorter than rule r2
        A rule is shorter if it has fewer atoms
        """
        r1_atoms = set(r1.split(" ∧ "))
        r2_atoms = set(r2.split(" ∧ "))
        
        return len(r1_atoms) < len(r2_atoms)
    
    def display_results(self, rules_type="final"):
        """Display rules with their statistics"""
        if rules_type == "frequent":
            rules = self.freq_rules
            title = "FREQUENT RULES"
        elif rules_type == "reliable":
            rules = self.rel_rules
            title = "RELIABLE RULES"
        else:
            rules = self.final_rules
            title = "FINAL RHAPSODY RULES"
            
        print(f"\n{title}:")
        if not rules:
            print("No rules found.")
            return
        
        for rule in rules:
            print(f"{rule}  |  nU×P: {self.nUP[rule]}  |  nA: {self.nA[rule]}")
    
    def get_rule_statistics(self):
        """Get comprehensive statistics about the mined rules"""
        return {
            'total_transactions': len(self.transactions),
            'frequent_rules_count': len(self.freq_rules),
            'reliable_rules_count': len(self.rel_rules),
            'final_rules_count': len(self.final_rules),
            'working_columns': self.working_columns,
            'rules': {
                'frequent': self.freq_rules,
                'reliable': self.rel_rules,
                'final': self.final_rules
            },
            'nUP': self.nUP,
            'nA': self.nA
        }
    
    def save_results(self, output_path):
        """Save results to JSON file"""
        results = self.get_rule_statistics()
        
        # Convert sets to lists for JSON serialization
        json_results = {
            'total_transactions': results['total_transactions'],
            'frequent_rules_count': results['frequent_rules_count'],
            'reliable_rules_count': results['reliable_rules_count'],
            'final_rules_count': results['final_rules_count'],
            'working_columns': results['working_columns'],
            'final_rules': results['rules']['final'],
            'nUP': results['nUP'],
            'nA': results['nA']
        }
        
        with open(output_path, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        print(f"Results saved to {output_path}")


# Standalone functions for backward compatibility
def rhapsody_algorithm(data_path, T, K, selected_columns=None):
    """
    Standalone function wrapper for the RHAPSODY algorithm
    """
    rhapsody = RhapsodyAlgorithm(selected_columns=selected_columns)
    rhapsody.load_data(data_path)
    final_rules, nUP, nA = rhapsody.run_algorithm(T, K)
    return final_rules, nUP, nA


def stage1(data, T, selected_columns=None):
    """Standalone Stage 1 function"""
    rhapsody = RhapsodyAlgorithm(selected_columns=selected_columns)
    rhapsody.load_data_from_dataframe(data)
    freq_rules, nUP, nA = rhapsody._stage1(T)
    return freq_rules, nUP, nA


def stage2(freq_rules, nUP, nA, T, K, selected_columns=None):
    """Standalone Stage 2 function"""
    rhapsody = RhapsodyAlgorithm(selected_columns=selected_columns)
    rhapsody.freq_rules = freq_rules
    rhapsody.nUP = nUP
    rhapsody.nA = nA
    rel_rules = rhapsody._stage2(T, K)
    return rel_rules


def stage3(rel_rules, nUP, nA, freq_rules, selected_columns=None):
    """Standalone Stage 3 function"""
    rhapsody = RhapsodyAlgorithm(selected_columns=selected_columns)
    rhapsody.rel_rules = rel_rules
    rhapsody.nUP = nUP
    rhapsody.nA = nA
    rhapsody.freq_rules = freq_rules
    short_rules = rhapsody._stage3()
    return short_rules


def proves_unreliability(r1, r2, nUP, T, K, selected_columns=None):
    """Standalone function for checking unreliability"""
    rhapsody = RhapsodyAlgorithm(selected_columns=selected_columns)
    rhapsody.nUP = nUP
    return rhapsody._proves_unreliability(r1, r2, T, K)


def are_equivalent(r1, r2, nUP, freq_rules, selected_columns=None):
    """Standalone function for checking rule equivalence"""
    rhapsody = RhapsodyAlgorithm(selected_columns=selected_columns)
    rhapsody.nUP = nUP
    rhapsody.freq_rules = freq_rules
    return rhapsody._are_equivalent(r1, r2)


def display_results(rules, nUP, nA, title):
    """Display rules with their statistics"""
    print(f"\n{title}:")
    if not rules:
        print("No rules found.")
        return

    for rule in rules:
        print(f"{rule}  |  nU×P: {nUP[rule]}  |  nA: {nA[rule]}")