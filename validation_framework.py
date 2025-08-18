#!/usr/bin/env python3
"""
Validation Framework for Platform Projections Model
Tests DAX calculations using Python to validate Power BI results
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

class ProjectionValidator:
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
        
    def interpolate_value(self, input_type, month, scenario="Base"):
        """
        Interpolate value for any input type and month
        Mimics the DAX GetInterpolatedValue measure
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
        
        # Apply scenario multiplier
        scenario_multipliers = {
            "Base": 1.0,
            "High_10": 1.1,
            "Low_10": 0.9,
            "High_25": 1.25,
            "Low_25": 0.75,
            "Custom": 1.0  # Would be variable in real implementation
        }
        
        multiplier = scenario_multipliers.get(scenario, 1.0)
        return base_value * multiplier
    
    def calculate_accounts(self, month, scenario="Base"):
        """Calculate account metrics for a given month"""
        total_accounts = self.interpolate_value("Accounts", month, scenario)
        active_share = self.interpolate_value("ActiveShare", month, scenario)
        checking_share = self.interpolate_value("CheckingShare", month, scenario)
        savings_share = self.interpolate_value("SavingShare", month, scenario)
        
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
        
        # Transaction volumes
        transactions = {
            'ach_incoming': active_accounts * self.interpolate_value("ACHinPerActive", month, scenario),
            'ach_outgoing': active_accounts * self.interpolate_value("ACHoutPerActive", month, scenario),
            'rtp_incoming': active_accounts * self.interpolate_value("RTPinPerActive", month, scenario),
            'rtp_outgoing': active_accounts * self.interpolate_value("RTPoutPerActive", month, scenario),
            'wire_incoming': active_accounts * self.interpolate_value("WireInPerActive", month, scenario),
            'wire_outgoing': active_accounts * self.interpolate_value("WireOutPerActive", month, scenario),
            'debit_card': active_accounts * self.interpolate_value("DebitCardTransactionsPerActive", month, scenario)
        }
        
        transactions['total_volume'] = sum(transactions.values())
        return transactions
    
    def calculate_revenue(self, month, scenario="Base"):
        """Calculate revenue for a given month"""
        transactions = self.calculate_transactions(month, scenario)
        
        revenue = {
            'ach_incoming': transactions['ach_incoming'] * self.interpolate_value("ACHinRate", month, scenario),
            'ach_outgoing': transactions['ach_outgoing'] * self.interpolate_value("ACHoutRate", month, scenario),
            'rtp_incoming': transactions['rtp_incoming'] * self.interpolate_value("RTPinRate", month, scenario),
            'rtp_outgoing': transactions['rtp_outgoing'] * self.interpolate_value("RTPoutRate", month, scenario),
            'wire_incoming': transactions['wire_incoming'] * self.interpolate_value("WireInRate", month, scenario),
            'wire_outgoing': transactions['wire_outgoing'] * self.interpolate_value("WireOutRate", month, scenario),
            'debit_card': transactions['debit_card'] * self.interpolate_value("DebitCardTransactionRate", month, scenario)
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
    
    def validate_interpolation(self, input_type, test_months=[2, 5, 7, 11, 13, 23, 25, 35]):
        """Validate interpolation logic for specific input type"""
        print(f"🔍 Validating interpolation for {input_type}...")
        
        results = []
        for month in test_months:
            interpolated = self.interpolate_value(input_type, month)
            results.append({
                'InputType': input_type,
                'Month': month,
                'InterpolatedValue': interpolated
            })
        
        return pd.DataFrame(results)
    
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
        df['VarianceFromBase'] = (df['TotalRevenue'] - base_revenue) / base_revenue
        
        return df
    
    def export_validation_results(self, output_dir="validation_output"):
        """Export comprehensive validation results"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print("📁 Exporting validation results...")
        
        # 1. Full test data for 36 months
        test_data = self.generate_test_data()
        test_data.to_csv(output_path / "test_data_36_months.csv", index=False)
        
        # 2. Interpolation validation for key input types
        key_inputs = ["Accounts", "ACHinPerActive", "ACHinRate", "DebitCardTransactionsPerActive"]
        interpolation_results = []
        for input_type in key_inputs:
            if input_type in self.parameters.index:
                result = self.validate_interpolation(input_type)
                interpolation_results.append(result)
        
        if interpolation_results:
            pd.concat(interpolation_results).to_csv(output_path / "interpolation_validation.csv", index=False)
        
        # 3. Scenario comparison for key months
        scenario_comparisons = []
        for month in [1, 6, 12, 24, 36]:
            comparison = self.compare_scenarios(month)
            scenario_comparisons.append(comparison)
        
        pd.concat(scenario_comparisons).to_csv(output_path / "scenario_comparisons.csv", index=False)
        
        # 4. Key metrics summary
        summary_data = []
        for month in [1, 6, 12, 24, 36]:
            accounts = self.calculate_accounts(month)
            revenue = self.calculate_revenue(month)
            summary_data.append({
                'Month': month,
                'TotalAccounts': accounts['total_accounts'],
                'TotalRevenue': revenue['total_revenue'],
                'RevenuePerAccount': revenue['total_revenue'] / accounts['total_accounts']
            })
        
        pd.DataFrame(summary_data).to_csv(output_path / "key_metrics_summary.csv", index=False)
        
        print(f"✅ Validation results exported to {output_path}")
        return output_path
    
    def print_sample_calculations(self):
        """Print sample calculations for verification"""
        print("\n🔢 Sample Calculations for Verification")
        print("=" * 50)
        
        for month in [1, 6, 12, 24, 36]:
            print(f"\n📅 Month {month}:")
            accounts = self.calculate_accounts(month)
            transactions = self.calculate_transactions(month)
            revenue = self.calculate_revenue(month)
            
            print(f"   Total Accounts: {accounts['total_accounts']:,.0f}")
            print(f"   Active Accounts: {accounts['active_accounts']:,.0f}")
            print(f"   Total Transactions: {transactions['total_volume']:,.0f}")
            print(f"   Total Revenue: ${revenue['total_revenue']:,.2f}")
            print(f"   Revenue/Account: ${revenue['total_revenue']/accounts['total_accounts']:,.2f}")

def main():
    """Main validation function"""
    print("🧪 Platform Projections Model Validation")
    print("=" * 50)
    
    validator = ProjectionValidator()
    
    # Generate validation results
    output_path = validator.export_validation_results()
    
    # Print sample calculations
    validator.print_sample_calculations()
    
    print(f"\n✅ Validation complete! Results saved to: {output_path}")
    print("\n📋 Files generated:")
    print("   - test_data_36_months.csv: Complete test data for all scenarios")
    print("   - interpolation_validation.csv: Interpolation accuracy tests")
    print("   - scenario_comparisons.csv: Scenario comparison analysis")
    print("   - key_metrics_summary.csv: Summary of key metrics")
    
    print("\n🎯 Use these files to:")
    print("   1. Compare Power BI results with Python calculations")
    print("   2. Validate interpolation accuracy") 
    print("   3. Test scenario switching functionality")
    print("   4. Verify revenue calculations")

if __name__ == "__main__":
    main()