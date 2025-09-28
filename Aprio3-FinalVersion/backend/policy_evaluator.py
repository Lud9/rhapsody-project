"""
Policy Evaluator for RHAPSODY Algorithm
Author: Ludjina
Description: Evaluates access requests against mined ABAC policies
"""

import json
from typing import Dict, List, Tuple


class PolicyEvaluator:
    """
    Policy Evaluator for ABAC (Attribute-Based Access Control)
    
    This class evaluates access requests against policies mined by the RHAPSODY algorithm.
    It determines whether access should be granted or denied based on matching rules.
    """
    
    def __init__(self, rules: List[str] = None):
        """
        Initialize the PolicyEvaluator
        
        Args:
            rules (List[str]): List of policy rules in string format
        """
        self.rules = rules or []
        self.rule_statistics = {}
        self.available_attributes = set()
        
    def load_rules(self, rules: List[str]):
        """
        Load policy rules into the evaluator
        
        Args:
            rules (List[str]): List of policy rules
        """
        self.rules = rules
        # Extract available attributes from rules
        self.available_attributes = set()
        for rule in self.rules:
            rule_attrs = self.parse_rule(rule)
            self.available_attributes.update(rule_attrs.keys())
        print(f"Loaded {len(self.rules)} policy rules")
        print(f"Available attributes: {sorted(self.available_attributes)}")
        
    def load_rules_from_file(self, file_path: str):
        """
        Load rules from a JSON file (typically from RHAPSODY output)
        
        Args:
            file_path (str): Path to JSON file containing rules
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.rules = data.get('final_rules', [])
                self.rule_statistics = {
                    'nUP': data.get('nUP', {}),
                    'nA': data.get('nA', {}),
                    'total_transactions': data.get('total_transactions', 0),
                    'final_rules_count': data.get('final_rules_count', 0)
                }
            print(f"Loaded {len(self.rules)} rules from {file_path}")
            return True
        except Exception as e:
            print(f"Error loading rules from file: {e}")
            return False
    
    def parse_rule(self, rule: str) -> Dict[str, str]:
        """
        Parse a rule string into a dictionary of attributes
        
        Args:
            rule (str): Rule in format "attr1=val1 ∧ attr2=val2 ∧ ..."
            
        Returns:
            Dict[str, str]: Dictionary mapping attributes to values
        """
        rule_dict = {}
        atoms = rule.split(' ∧ ')
        
        for atom in atoms:
            if '=' in atom:
                attr, value = atom.split('=', 1)
                rule_dict[attr.strip()] = value.strip()
                
        return rule_dict
    
    def rule_matches_request(self, rule: str, request: Dict[str, str]) -> bool:
        """
        Check if a rule matches an access request
        """
        rule_attrs = self.parse_rule(rule)
        
        # Check if all rule attributes that have values in request match
        for attr, rule_value in rule_attrs.items():
            request_value = request.get(attr, '').strip()
            
            # Skip if request doesn't have this attribute or it's empty
            if not request_value:
                continue
                
            # Must match exactly if both have values
            if request_value != rule_value:
                return False
        
        # Must have at least one matching attribute
        matching_attrs = 0
        for attr, rule_value in rule_attrs.items():
            request_value = request.get(attr, '').strip()
            if request_value and request_value == rule_value:
                matching_attrs += 1
        
        return matching_attrs > 0
    
    def evaluate_request(self, request: Dict[str, str]) -> Dict:
        """
        Evaluate an access request against loaded policy rules
        
        Args:
            request (Dict[str, str]): Access request with attributes
            
        Returns:
            Dict: Evaluation result containing decision and details
        """
        if not self.rules:
            return {
                'granted': False,
                'message': "No policy rules available. Please load rules first.",
                'matching_rule': None,
                'request_details': request
            }
        
        # Check if request has at least one attribute filled
        has_attributes = any(
            value.strip() != '' for key, value in request.items() 
            if key in self.available_attributes
        )
        if not has_attributes:
            return {
                'granted': False,
                'message': "Please fill in at least one attribute.",
                'matching_rule': None,
                'request_details': request
            }
        
        # Find matching rule
        for rule in self.rules:
            if self.rule_matches_request(rule, request):
                return {
                    'granted': True,
                    'message': "Access Granted! Request matches a mined policy rule.",
                    'matching_rule': rule,
                    'request_details': request,
                    'rule_statistics': self.rule_statistics.get('nUP', {}).get(rule, 'N/A')
                }
        
        return {
            'granted': False,
            'message': "Access Denied! No matching rule found in the mined policy.",
            'matching_rule': None,
            'request_details': request
        }
    
    def batch_evaluate(self, requests: List[Dict[str, str]]) -> List[Dict]:
        """
        Evaluate multiple access requests
        
        Args:
            requests (List[Dict[str, str]]): List of access requests
            
        Returns:
            List[Dict]: List of evaluation results
        """
        results = []
        for request in requests:
            result = self.evaluate_request(request)
            results.append(result)
        
        return results
    
    def get_rule_coverage_stats(self) -> Dict:
        """
        Get statistics about rule coverage and usage
        
        Returns:
            Dict: Statistics about the loaded rules
        """
        if not self.rules:
            return {"error": "No rules loaded"}
        
        stats = {
            'total_rules': len(self.rules),
            'rules_by_complexity': {},
            'attribute_distribution': {}
        }
        
        # Analyze rule complexity (number of attributes)
        for rule in self.rules:
            num_attrs = len(rule.split(' ∧ '))
            if num_attrs not in stats['rules_by_complexity']:
                stats['rules_by_complexity'][num_attrs] = 0
            stats['rules_by_complexity'][num_attrs] += 1
        
        # Analyze attribute distribution
        attr_counts = {}
        for rule in self.rules:
            rule_attrs = self.parse_rule(rule)
            for attr in rule_attrs:
                if attr not in attr_counts:
                    attr_counts[attr] = 0
                attr_counts[attr] += 1
        
        stats['attribute_distribution'] = attr_counts
        
        return stats
    
    def find_conflicting_rules(self) -> List[Tuple[str, str]]:
        """
        Find potentially conflicting rules (rules that might contradict each other)
        
        Returns:
            List[Tuple[str, str]]: List of rule pairs that might conflict
        """
        conflicts = []
        
        for i, rule1 in enumerate(self.rules):
            for j, rule2 in enumerate(self.rules[i+1:], i+1):
                rule1_attrs = self.parse_rule(rule1)
                rule2_attrs = self.parse_rule(rule2)
                
                # Check if rules have overlapping attributes with different values
                overlap = set(rule1_attrs.keys()) & set(rule2_attrs.keys())
                if overlap:
                    has_conflict = any(
                        rule1_attrs[attr] != rule2_attrs[attr] 
                        for attr in overlap
                    )
                    if has_conflict:
                        conflicts.append((rule1, rule2))
        
        return conflicts
    
    def generate_test_requests(self, num_requests: int = 10) -> List[Dict[str, str]]:
        """
        Generate test requests based on loaded rules
        
        Args:
            num_requests (int): Number of test requests to generate
            
        Returns:
            List[Dict[str, str]]: List of test requests
        """
        if not self.rules:
            return []
        
        test_requests = []
        
        # Extract all possible attribute values from rules
        all_attrs = {}
        for rule in self.rules:
            rule_attrs = self.parse_rule(rule)
            for attr, value in rule_attrs.items():
                if attr not in all_attrs:
                    all_attrs[attr] = set()
                all_attrs[attr].add(value)
        
        # Generate test requests
        import random
        for _ in range(num_requests):
            request = {}
            # Randomly select attributes and values
            selected_attrs = random.sample(
                list(all_attrs.keys()), 
                min(len(all_attrs), random.randint(1, len(all_attrs)))
            )
            
            for attr in selected_attrs:
                request[attr] = random.choice(list(all_attrs[attr]))
            
            test_requests.append(request)
        
        return test_requests
    
    def get_available_attributes(self) -> List[str]:
        """
        Get list of available attributes from loaded rules
        
        Returns:
            List[str]: List of available attribute names
        """
        return sorted(list(self.available_attributes))
    
    def export_evaluation_report(self, requests: List[Dict[str, str]], 
                                output_file: str = "evaluation_report.json"):
        """
        Generate and export a comprehensive evaluation report
        
        Args:
            requests (List[Dict[str, str]]): List of requests to evaluate
            output_file (str): Output file path
        """
        results = self.batch_evaluate(requests)
        
        # Calculate statistics
        granted_count = sum(1 for r in results if r['granted'])
        denied_count = len(results) - granted_count
        
        report = {
            'evaluation_summary': {
                'total_requests': len(requests),
                'granted': granted_count,
                'denied': denied_count,
                'grant_rate': granted_count / len(requests) if requests else 0
            },
            'rule_statistics': self.get_rule_coverage_stats(),
            'detailed_results': results,
            'policy_rules': self.rules
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Evaluation report exported to {output_file}")
        return report
    
    def set_available_attributes(self, attributes):
        """Set available attributes explicitly"""
        self.available_attributes = set(attributes)


# Utility functions for standalone usage
def create_access_request(**kwargs) -> Dict[str, str]:
    """
    Create a standardized access request with dynamic attributes
    
    Args:
        **kwargs: Dynamic attributes and their values
        
    Returns:
        Dict[str, str]: Formatted access request
    """
    return {key: str(value) for key, value in kwargs.items()}


def evaluate_single_request(rules: List[str], request: Dict[str, str]) -> Dict:
    """
    Standalone function to evaluate a single request
    
    Args:
        rules (List[str]): List of policy rules
        request (Dict[str, str]): Access request
        
    Returns:
        Dict: Evaluation result
    """
    evaluator = PolicyEvaluator(rules)
    return evaluator.evaluate_request(request)
