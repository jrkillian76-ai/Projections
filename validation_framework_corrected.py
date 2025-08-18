#!/usr/bin/env python3
"""
Validation Framework for Platform Projections Model - CORRECTED
Tests DAX calculations where scenarios ONLY affect Accounts, not other variables
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

class ProjectionValidatorCorrected:
    def __init__(self, excel_file="Projection_Inputs_v1.0.xlsx"):
        self.excel_file = excel_file
        self.parameters = None
        self.load_parameters()
    
    def load_parameters(self):
        """Load parameters from Excel file"""
        print("📊 Loading parameters from Excel...")
        
        # Load the main parameters sheet
        df = pd.read_excel(self.excel_file, sheet_name='MonthlyInputs')
        self.parameters = df.pivot_table(
            index='InputType', 
            columns='Month', 
            values='Value', 
            aggfunc='first'
        )
        
        print(f"✅ Loaded {len(self.parameters)} input types across {len(self.parameters.columns)} months")
        
    def interpolate_value(self, input_type, month):
        """
        Interpolate value for any input type and month
        NO SCENARIO ADJUSTMENT - returns base values only
        """
        if input_type not in self.parameters.index:
            return 0
        
        row = self.parameters.loc[input_type]
        
        # Key month values
        m1_val = row.get(1, 0)
        m6_val = row.get(6, 0)
        m12_val = row.get(12, 0)
        m24_val = row.get(24, 0)
        m36_val = row.get(36, 0)
        
        # Interpolation logic (same as DAX)
        if month == 1:
            base_value = m1_val
        elif month <= 6:
            base_value = m1_val + (m6_val - m1_val) * (month - 1) / 5
        elif month <= 12:
            base_value = m6_val + (m12_val - m6_val) * (month - 6) / 6
        elif month <= 24:
            base_value = m12_val + (m24_val - m12_val) * (month - 12) / 12
        elif month <= 36:
            base_value = m24_val + (m36_val - m24_val) * (month - 24) / 12
        else:
            # Beyond month 36, apply growth rate
            growth_rate = self.parameters.loc['GrowthRateM37Plus', 37] if 'GrowthRateM37Plus' in self.parameters.index else 0.01
            base_value = m36_val * ((1 + growth_rate) ** (month - 36))
        
        return base_value
    
    def get_accounts_with_scenario(self, month, scenario="Base"):
        """
        Get accounts with scenario adjustment
        ONLY Accounts are affected by scenarios
        """
        base_accounts = self.interpolate_value("Accounts", month)
        
        # Apply scenario multiplier ONLY to accounts
        scenario_multipliers = {
            "Base": 1.0,
            "High_10": 1.1,
            "Low_10": 0.9,
            "High_25": 1.25,
            "Low_25": 0.75,
            "Custom": 1.0  # Would be variable in real implementation
        }
        
        multiplier = scenario_multipliers.get(scenario, 1.0)
        return base_accounts * multiplier
    
    def calculate_accounts(self, month, scenario="Base"):
        """Calculate account metrics for a given month"""
        total_accounts = self.get_accounts_with_scenario(month, scenario)
        
        # These rates are NOT affected by scenarios - use base interpolation
        active_share = self.interpolate_value("ActiveShare", month)
        checking_share = self.interpolate_value("CheckingShare", month)
        savings_share = self.interpolate_value("SavingShare", month)
        
        active_accounts = total_accounts * active_share
        checking_accounts = active_accounts * checking_share
        savings_accounts = active_accounts * savings_share
        
        return {
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'checking_accounts': checking_accounts,
            'savings_accounts': savings_accounts
        }
    
    def calculate_transactions(self, month, scenario="Base"):
        """Calculate transaction volumes for a given month"""
        accounts = self.calculate_accounts(month, scenario)
        active_accounts = accounts['active_accounts']
        
        # Transaction rates are NOT affected by scenarios - use base interpolation
        transactions = {
            'ach_incoming': active_accounts * self.interpolate_value("ACHinPerActive", month),
            'ach_outgoing': active_accounts * self.interpolate_value("ACHoutPerActive", month),
            'rtp_incoming': active_accounts * self.interpolate_value("RTPinPerActive", month),
            'rtp_outgoing': active_accounts * self.interpolate_value("RTPoutPerActive", month),
            'wire_incoming': active_accounts * self.interpolate_value("WireInPerActive", month),
            'wire_outgoing': active_accounts * self.interpolate_value("WireOutPerActive", month),
            'debit_card': active_accounts * self.interpolate_value("DebitCardTransactionsPerActive", month)
        }
        
        transactions['total_volume'] = sum(transactions.values())
        return transactions
    
    def calculate_revenue(self, month, scenario="Base"):
        """Calculate revenue for a given month"""
        transactions = self.calculate_transactions(month, scenario)
        
        # Revenue rates are NOT affected by scenarios - use base interpolation
        revenue = {
            'ach_incoming': transactions['ach_incoming'] * self.interpolate_value("ACHinRate", month),
            'ach_outgoing': transactions['ach_outgoing'] * self.interpolate_value("ACHoutRate", month),
            'rtp_incoming': transactions['rtp_incoming'] * self.interpolate_value("RTPinRate", month),
            'rtp_outgoing': transactions['rtp_outgoing'] * self.interpolate_value("RTPoutRate", month),
            'wire_incoming': transactions['wire_incoming'] * self.interpolate_value("WireInRate", month),
            'wire_outgoing': transactions['wire_outgoing'] * self.interpolate_value("WireOutRate", month),
            'debit_card': transactions['debit_card'] * self.interpolate_value("DebitCardTransactionRate", month)
        }
        
        revenue['total_revenue'] = sum(revenue.values())
        return revenue
    
    def generate_test_data(self, months_range=(1, 37), scenarios=["Base", "High_10", "Low_10"]):
        """Generate test data for validation"""
        print("🧪 Generating test data for validation...")
        
        test_data = []
        
        for month in range(months_range[0], months_range[1]):
            for scenario in scenarios:
                accounts = self.calculate_accounts(month, scenario)
                transactions = self.calculate_transactions(month, scenario)
                revenue = self.calculate_revenue(month, scenario)
                
                row = {
                    'Month': month,
                    'Scenario': scenario,
                    **{f'Accounts_{k}': v for k, v in accounts.items()},
                    **{f'Transactions_{k}': v for k, v in transactions.items()},
                    **{f'Revenue_{k}': v for k, v in revenue.items()}
                }
                
                test_data.append(row)
        
        df = pd.DataFrame(test_data)
        return df
    
    def compare_scenarios(self, month=12):
        """Compare all scenarios for a specific month"""
        print(f"📊 Comparing scenarios for Month {month}...")
        
        scenarios = ["Base", "High_10", "Low_10", "High_25", "Low_25"]
        comparison = []
        
        for scenario in scenarios:
            accounts = self.calculate_accounts(month, scenario)
            revenue = self.calculate_revenue(month, scenario)
            
            comparison.append({
                'Scenario': scenario,
                'Month': month,
                'TotalAccounts': accounts['total_accounts'],
                'ActiveAccounts': accounts['active_accounts'],
                'TotalRevenue': revenue['total_revenue'],
                'RevenuePerAccount': revenue['total_revenue'] / accounts['total_accounts'] if accounts['total_accounts'] > 0 else 0
            })
        
        df = pd.DataFrame(comparison)
        
        # Calculate variance from base
        base_revenue = df[df['Scenario'] == 'Base']['TotalRevenue'].iloc[0]
        base_accounts = df[df['Scenario'] == 'Base']['TotalAccounts'].iloc[0]
        
        df['VarianceFromBase_Revenue'] = (df['TotalRevenue'] - base_revenue) / base_revenue
        df['VarianceFromBase_Accounts'] = (df['TotalAccounts'] - base_accounts) / base_accounts
        
        return df
    
    def print_scenario_verification(self):
        """Print scenario verification to show only accounts change"""
        print("\n🔢 Scenario Verification - Only Accounts Should Change")
        print("=" * 70)
        
        month = 12  # Test with month 12
        scenarios = ["Base", "High_10", "Low_10"]
        
        for scenario in scenarios:
            print(f"\n📅 Month {month} - {scenario} Scenario:")
            
            accounts = self.calculate_accounts(month, scenario)
            
            # Check rates (should be same across scenarios)
            ach_in_rate = self.interpolate_value("ACHinPerActive", month)
            ach_in_fee = self.interpolate_value("ACHinRate", month)
            active_share = self.interpolate_value("ActiveShare", month)
            
            print(f"   Total Accounts: {accounts['total_accounts']:,.0f}")
            print(f"   ACH In Per Active: {ach_in_rate:.2f} (should be same)")
            print(f"   ACH In Rate: ${ach_in_fee:,.0f} (should be same)")
            print(f"   Active Share: {active_share:.1%} (should be same)")
        
        print(f"\n✅ Verification: Only account numbers should differ between scenarios")
        print(f"   All rates, fees, and percentages should remain identical")
    
    def export_validation_results(self, output_dir="validation_output_corrected"):
        """Export comprehensive validation results"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print("📁 Exporting corrected validation results...")
        
        # 1. Full test data for 36 months
        test_data = self.generate_test_data()
        test_data.to_csv(output_path / "test_data_36_months_corrected.csv", index=False)
        
        # 2. Scenario comparison for key months
        scenario_comparisons = []
        for month in [1, 6, 12, 24, 36]:
            comparison = self.compare_scenarios(month)
            scenario_comparisons.append(comparison)
        
        pd.concat(scenario_comparisons).to_csv(output_path / "scenario_comparisons_corrected.csv", index=False)
        
        # 3. Rate verification (should be same across scenarios)
        rate_verification = []
        for month in [1, 6, 12, 24, 36]:
            row = {
                'Month': month,
                'ACHinPerActive': self.interpolate_value("ACHinPerActive", month),
                'ACHinRate': self.interpolate_value("ACHinRate", month),
                'ActiveShare': self.interpolate_value("ActiveShare", month),
                'CheckingShare': self.interpolate_value("CheckingShare", month),
                'RTPinRate': self.interpolate_value("RTPinRate", month),
                'DebitCardTransactionRate': self.interpolate_value("DebitCardTransactionRate", month)
            }
            rate_verification.append(row)
        
        pd.DataFrame(rate_verification).to_csv(output_path / "rate_verification.csv", index=False)
        
        print(f"✅ Corrected validation results exported to {output_path}")
        return output_path

def main():
    """Main validation function"""
    print("🧪 Platform Projections Model Validation - CORRECTED")
    print("📝 Scenarios only affect Accounts, not other variables")
    print("=" * 60)
    
    validator = ProjectionValidatorCorrected()
    
    # Generate validation results
    output_path = validator.export_validation_results()
    
    # Print scenario verification
    validator.print_scenario_verification()
    
    print(f"\n✅ Corrected validation complete! Results saved to: {output_path}")
    print("\n📋 Files generated:")
    print("   - test_data_36_months_corrected.csv: Complete test data")
    print("   - scenario_comparisons_corrected.csv: Scenario comparison analysis")
    print("   - rate_verification.csv: Verify rates are constant across scenarios")
    
    print("\n🎯 Key change:")
    print("   - Scenarios only modify account growth")
    print("   - All rates, fees, and percentages remain constant")
    print("   - Revenue changes proportionally to account changes only")

if __name__ == "__main__":
    main()