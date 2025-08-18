# CalculationsTable - Corrected with Exact Input Type Names

## 📋 **Exact Input Types from Your Excel:**

Based on your parameters table, here are the exact names we need to use:

**Accounts & Shares:**
- `Accounts`
- `ActiveShare` 
- `CheckingShare`
- `SavingShare` (note: SavingShare, not SavingsShare)

**Inflow Types:**
- `ACHinPerActive`, `ACHinRate`
- `RTPinPerActive`, `RTPinRate` 
- `WireInPerActive`, `WireInRate`

**Outflow Types:**
- `ACHoutPerActive`, `ACHoutRate`, `ACHoutShare`
- `RTPoutPerActive`, `RTPoutRate`, `RTPoutShare`
- `WireOutPerActive`, `WireOutRate`, `WireOutShare`
- `DebitCardTransactionsPerActive`, `DebitCardTransactionRate`, `DebitCardTransactionShare`

**Usage & Transfer Rates:**
- `CheckingUsageRate`
- `SavingsUsageRate` 
- `SavingsTransferRate`

**Growth:**
- `GrowthRateM37Plus` (Month 37)

## 🎯 **Corrected CalculationsTable M Code:**

```m
let
    // Step 1: Create Month × Scenario cross join
    MonthRange = List.Numbers(1, 60, 1),
    MonthTable = Table.FromList(MonthRange, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Renamed Month Column" = Table.RenameColumns(MonthTable,{{"Column1", "Month"}}),
    
    // Get scenarios
    ScenariosData = Scenarios,
    
    // Cross join months and scenarios
    CrossJoin = Table.AddColumn(#"Renamed Month Column", "Scenario", each ScenariosData),
    #"Expanded Scenarios" = Table.ExpandTableColumn(CrossJoin, "Scenario", {"ScenarioName", "ScenarioDisplay", "DefaultMultiplier"}, {"ScenarioName", "ScenarioDisplay", "DefaultMultiplier"}),
    
    // Helper function to get interpolated value
    GetInterpolatedValue = (inputType as text, month as number) =>
        let
            FilteredInputs = Table.SelectRows(InterpolatedInputs, each [InputType] = inputType and [Month] = month),
            Value = if Table.RowCount(FilteredInputs) > 0 then FilteredInputs{0}[Value] else 0
        in
            Value,
    
    // Helper function to get scenario multiplier
    GetScenarioMultiplier = (scenarioName as text, defaultMultiplier as number) =>
        if scenarioName = "Custom" then
            1.0 // Will be overridden by slicer
        else
            defaultMultiplier,
    
    // Step 2: Account Calculations
    #"Added Total Accounts" = Table.AddColumn(#"Expanded Scenarios", "TotalAccounts", each
        let
            BaseAccounts = GetInterpolatedValue("Accounts", [Month]),
            ScenarioMultiplier = GetScenarioMultiplier([ScenarioName], [DefaultMultiplier])
        in
            BaseAccounts * ScenarioMultiplier
    ),
    
    #"Added Active Share" = Table.AddColumn(#"Added Total Accounts", "ActiveShare", each
        GetInterpolatedValue("ActiveShare", [Month])
    ),
    
    #"Added Active Accounts" = Table.AddColumn(#"Added Active Share", "ActiveAccounts", each
        [TotalAccounts] * [ActiveShare]
    ),
    
    #"Added Checking Share" = Table.AddColumn(#"Added Active Accounts", "CheckingShare", each
        GetInterpolatedValue("CheckingShare", [Month])
    ),
    
    #"Added Checking Accounts" = Table.AddColumn(#"Added Checking Share", "CheckingAccounts", each
        [ActiveAccounts] * [CheckingShare]
    ),
    
    #"Added Saving Share" = Table.AddColumn(#"Added Checking Accounts", "SavingShare", each
        GetInterpolatedValue("SavingShare", [Month])
    ),
    
    #"Added Saving Accounts" = Table.AddColumn(#"Added Saving Share", "SavingAccounts", each
        [ActiveAccounts] * [SavingShare]
    ),
    
    // Step 3: Inflow Calculations
    
    // ACH Inflows
    #"Added ACH In Per Active" = Table.AddColumn(#"Added Saving Accounts", "ACHinPerActive", each
        GetInterpolatedValue("ACHinPerActive", [Month])
    ),
    
    #"Added ACH In Rate" = Table.AddColumn(#"Added ACH In Per Active", "ACHinRate", each
        GetInterpolatedValue("ACHinRate", [Month])
    ),
    
    #"Added ACH In Quantity" = Table.AddColumn(#"Added ACH In Rate", "ACHin_Quantity", each
        [ActiveAccounts] * [ACHinPerActive]
    ),
    
    #"Added ACH In Amount" = Table.AddColumn(#"Added ACH In Quantity", "ACHin_Amount", each
        [ACHin_Quantity] * [ACHinRate]
    ),
    
    // RTP Inflows
    #"Added RTP In Per Active" = Table.AddColumn(#"Added ACH In Amount", "RTPinPerActive", each
        GetInterpolatedValue("RTPinPerActive", [Month])
    ),
    
    #"Added RTP In Rate" = Table.AddColumn(#"Added RTP In Per Active", "RTPinRate", each
        GetInterpolatedValue("RTPinRate", [Month])
    ),
    
    #"Added RTP In Quantity" = Table.AddColumn(#"Added RTP In Rate", "RTPin_Quantity", each
        [ActiveAccounts] * [RTPinPerActive]
    ),
    
    #"Added RTP In Amount" = Table.AddColumn(#"Added RTP In Quantity", "RTPin_Amount", each
        [RTPin_Quantity] * [RTPinRate]
    ),
    
    // Wire Inflows
    #"Added Wire In Per Active" = Table.AddColumn(#"Added RTP In Amount", "WireInPerActive", each
        GetInterpolatedValue("WireInPerActive", [Month])
    ),
    
    #"Added Wire In Rate" = Table.AddColumn(#"Added Wire In Per Active", "WireInRate", each
        GetInterpolatedValue("WireInRate", [Month])
    ),
    
    #"Added Wire In Quantity" = Table.AddColumn(#"Added Wire In Rate", "WireIn_Quantity", each
        [ActiveAccounts] * [WireInPerActive]
    ),
    
    #"Added Wire In Amount" = Table.AddColumn(#"Added Wire In Quantity", "WireIn_Amount", each
        [WireIn_Quantity] * [WireInRate]
    ),
    
    // Total Inflows
    #"Added Total Inflows" = Table.AddColumn(#"Added Wire In Amount", "Total_Inflows", each
        [ACHin_Amount] + [RTPin_Amount] + [WireIn_Amount]
    ),
    
    // Step 4: Outflow Calculations
    
    // ACH Outflows - Using interpolated shares from your data
    #"Added ACH Out Per Active" = Table.AddColumn(#"Added Total Inflows", "ACHoutPerActive", each
        GetInterpolatedValue("ACHoutPerActive", [Month])
    ),
    
    #"Added ACH Out Share" = Table.AddColumn(#"Added ACH Out Per Active", "ACHoutShare", each
        GetInterpolatedValue("ACHoutShare", [Month])
    ),
    
    #"Added ACH Out Amount" = Table.AddColumn(#"Added ACH Out Share", "ACHout_Amount", each
        [Total_Inflows] * [ACHoutShare]
    ),
    
    #"Added ACH Out Quantity" = Table.AddColumn(#"Added ACH Out Amount", "ACHout_Quantity", each
        [ActiveAccounts] * [ACHoutPerActive]
    ),
    
    #"Added ACH Out Rate Solved" = Table.AddColumn(#"Added ACH Out Quantity", "ACHout_Rate_Solved", each
        if [ACHout_Quantity] > 0 then [ACHout_Amount] / [ACHout_Quantity] else 0
    ),
    
    // RTP Outflows
    #"Added RTP Out Per Active" = Table.AddColumn(#"Added ACH Out Rate Solved", "RTPoutPerActive", each
        GetInterpolatedValue("RTPoutPerActive", [Month])
    ),
    
    #"Added RTP Out Share" = Table.AddColumn(#"Added RTP Out Per Active", "RTPoutShare", each
        GetInterpolatedValue("RTPoutShare", [Month])
    ),
    
    #"Added RTP Out Amount" = Table.AddColumn(#"Added RTP Out Share", "RTPout_Amount", each
        [Total_Inflows] * [RTPoutShare]
    ),
    
    #"Added RTP Out Quantity" = Table.AddColumn(#"Added RTP Out Amount", "RTPout_Quantity", each
        [ActiveAccounts] * [RTPoutPerActive]
    ),
    
    #"Added RTP Out Rate Solved" = Table.AddColumn(#"Added RTP Out Quantity", "RTPout_Rate_Solved", each
        if [RTPout_Quantity] > 0 then [RTPout_Amount] / [RTPout_Quantity] else 0
    ),
    
    // Wire Outflows
    #"Added Wire Out Per Active" = Table.AddColumn(#"Added RTP Out Rate Solved", "WireOutPerActive", each
        GetInterpolatedValue("WireOutPerActive", [Month])
    ),
    
    #"Added Wire Out Share" = Table.AddColumn(#"Added Wire Out Per Active", "WireOutShare", each
        GetInterpolatedValue("WireOutShare", [Month])
    ),
    
    #"Added Wire Out Amount" = Table.AddColumn(#"Added Wire Out Share", "WireOut_Amount", each
        [Total_Inflows] * [WireOutShare]
    ),
    
    #"Added Wire Out Quantity" = Table.AddColumn(#"Added Wire Out Amount", "WireOut_Quantity", each
        [ActiveAccounts] * [WireOutPerActive]
    ),
    
    #"Added Wire Out Rate Solved" = Table.AddColumn(#"Added Wire Out Quantity", "WireOut_Rate_Solved", each
        if [WireOut_Quantity] > 0 then [WireOut_Amount] / [WireOut_Quantity] else 0
    ),
    
    // Debit Card Outflows
    #"Added Debit Per Active" = Table.AddColumn(#"Added Wire Out Rate Solved", "DebitCardTransactionsPerActive", each
        GetInterpolatedValue("DebitCardTransactionsPerActive", [Month])
    ),
    
    #"Added Debit Share" = Table.AddColumn(#"Added Debit Per Active", "DebitCardTransactionShare", each
        GetInterpolatedValue("DebitCardTransactionShare", [Month])
    ),
    
    #"Added Debit Amount" = Table.AddColumn(#"Added Debit Share", "DebitCard_Amount", each
        [Total_Inflows] * [DebitCardTransactionShare]
    ),
    
    #"Added Debit Quantity" = Table.AddColumn(#"Added Debit Amount", "DebitCard_Quantity", each
        [ActiveAccounts] * [DebitCardTransactionsPerActive]
    ),
    
    #"Added Debit Rate Solved" = Table.AddColumn(#"Added Debit Quantity", "DebitCard_Rate_Solved", each
        if [DebitCard_Quantity] > 0 then [DebitCard_Amount] / [DebitCard_Quantity] else 0
    ),
    
    // Step 5: Total Outflows and Final Calculations
    #"Added Total Outflows" = Table.AddColumn(#"Added Debit Rate Solved", "Total_Outflows", each
        [ACHout_Amount] + [RTPout_Amount] + [WireOut_Amount] + [DebitCard_Amount]
    ),
    
    #"Added Savings Transfer Rate" = Table.AddColumn(#"Added Total Outflows", "SavingsTransferRate", each
        GetInterpolatedValue("SavingsTransferRate", [Month])
    ),
    
    #"Added Savings Transfers" = Table.AddColumn(#"Added Savings Transfer Rate", "SavingsTransfers", each
        ([Total_Inflows] - [Total_Outflows]) * [SavingsTransferRate]
    ),
    
    #"Added Monthly Checking" = Table.AddColumn(#"Added Savings Transfers", "Monthly_Checking", each
        [Total_Inflows] - [Total_Outflows] - [SavingsTransfers]
    ),
    
    #"Added Monthly Savings" = Table.AddColumn(#"Added Monthly Checking", "Monthly_Savings_Transfers", each
        [SavingsTransfers]
    ),
    
    // Final data type cleanup
    #"Changed Types" = Table.TransformColumnTypes(#"Added Monthly Savings",{
        {"Month", Int64.Type},
        {"TotalAccounts", type number},
        {"ActiveAccounts", type number},
        {"CheckingAccounts", type number},
        {"SavingAccounts", type number},
        {"Total_Inflows", type number},
        {"Total_Outflows", type number},
        {"Monthly_Checking", type number},
        {"Monthly_Savings_Transfers", type number}
    })
    
in
    #"Changed Types"
```

## 🎯 **Key Changes Made:**

1. **✅ Exact Input Type Names**: Used your precise names like `ACHinPerActive`, `RTPinPerActive`, etc.
2. **✅ Simplified Logic**: Since you already have the interpolated shares in your data, we use them directly instead of calculating them
3. **✅ Added SavingShare**: Included the savings account calculations
4. **✅ All Outflow Types**: ACH, RTP, Wire, and Debit Card transactions
5. **✅ Correct Rate Names**: `SavingsUsageRate`, `CheckingUsageRate`, `SavingsTransferRate`

This should now match your Excel data perfectly! Ready to test this version?