# Table Replacement Strategy for v0.22 Model

## 🎯 **Plan: Replace Tables with Clean Implementation**

You'll replace the existing tables with optimized versions that work with the corrected scenario logic (scenarios only affect accounts).

---

## 📋 **Tables to Replace/Rebuild:**

### 1. **InterpolatedInputs** → **NEW: Complete Interpolated Data**
### 2. **CalcsTable** → **REBUILD: Clean Calculations Table**  
### 3. **PartnerTable** → **REBUILD: Partner-Specific Logic**

---

## 🔧 **1. NEW InterpolatedInputs Table (M Code)**

Replace your existing InterpolatedInputs with this M Code in Power Query:

```m
let
    // Source: Load Parameters from Excel
    Source = Excel.CurrentWorkbook(){[Name="Parameters"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"InputType", type text}, {"Month", Int64.Type}, {"Value", type number}}),
    
    // Create complete month range (1 to 60)
    MonthRange = List.Numbers(1, 60, 1),
    MonthTable = Table.FromList(MonthRange, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Renamed Month Column" = Table.RenameColumns(MonthTable,{{"Column1", "Month"}}),
    
    // Get unique input types
    InputTypes = Table.Distinct(#"Changed Type", {"InputType"}),
    
    // Cross join: Every month × Every input type
    CrossJoin = Table.AddColumn(#"Renamed Month Column", "InputType", each InputTypes),
    #"Expanded InputTypes" = Table.ExpandTableColumn(CrossJoin, "InputType", {"InputType"}, {"InputType"}),
    
    // Add interpolated values
    #"Added Interpolation" = Table.AddColumn(#"Expanded InputTypes", "Value", each 
        let
            CurrentInputType = [InputType],
            CurrentMonth = [Month],
            
            // Get key month values for this input type
            M1Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 1){0}[Value] otherwise 0,
            M6Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 6){0}[Value] otherwise M1Value,
            M12Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 12){0}[Value] otherwise M6Value,
            M24Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 24){0}[Value] otherwise M12Value,
            M36Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 36){0}[Value] otherwise M24Value,
            
            // Growth rate for beyond month 36
            GrowthRate = try Table.SelectRows(#"Changed Type", each [InputType] = "GrowthRateM37Plus" and [Month] = 37){0}[Value] otherwise 0.01,
            
            // Interpolation logic
            InterpolatedValue = 
                if CurrentMonth = 1 then M1Value
                else if CurrentMonth <= 6 then M1Value + (M6Value - M1Value) * (CurrentMonth - 1) / 5
                else if CurrentMonth <= 12 then M6Value + (M12Value - M6Value) * (CurrentMonth - 6) / 6
                else if CurrentMonth <= 24 then M12Value + (M24Value - M12Value) * (CurrentMonth - 12) / 12
                else if CurrentMonth <= 36 then M24Value + (M36Value - M24Value) * (CurrentMonth - 24) / 12
                else M36Value * Number.Power(1 + GrowthRate, CurrentMonth - 36)
        in
            InterpolatedValue
    ),
    
    // Clean up data types
    #"Changed Value Type" = Table.TransformColumnTypes(#"Added Interpolation",{{"Value", type number}}),
    
    // Reorder columns
    #"Reordered Columns" = Table.ReorderColumns(#"Changed Value Type",{"InputType", "Month", "Value"})
in
    #"Reordered Columns"
```

---

## 🔧 **2. NEW CalcsTable (M Code)**

Create a clean CalcsTable that handles scenarios properly:

```m
let
    // Get the interpolated inputs
    InterpolatedInputs = Table.FromRows({}, {"InputType", "Month", "Value"}), // Reference your new InterpolatedInputs table
    
    // Create month range
    MonthRange = List.Numbers(1, 60, 1),
    MonthTable = Table.FromList(MonthRange, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Renamed Month Column" = Table.RenameColumns(MonthTable,{{"Column1", "Month"}}),
    
    // Create scenarios
    Scenarios = Table.FromRows({
        {"Base", 1.0},
        {"High_10", 1.1},
        {"Low_10", 0.9},
        {"High_25", 1.25},
        {"Low_25", 0.75},
        {"Custom", 1.0}
    }, {"Scenario", "AccountMultiplier"}),
    
    // Cross join: Month × Scenario
    CrossJoin = Table.AddColumn(#"Renamed Month Column", "Scenario", each Scenarios),
    #"Expanded Scenarios" = Table.ExpandTableColumn(CrossJoin, "Scenario", {"Scenario", "AccountMultiplier"}, {"Scenario", "AccountMultiplier"}),
    
    // Add calculated metrics
    #"Added Calculations" = Table.AddColumn(#"Expanded Scenarios", "Calculations", each 
        let
            CurrentMonth = [Month],
            CurrentScenario = [Scenario],
            AccountMultiplier = [AccountMultiplier],
            
            // Helper function to get interpolated value
            GetValue = (inputType as text) => 
                let
                    FilteredTable = Table.SelectRows(InterpolatedInputs, each [InputType] = inputType and [Month] = CurrentMonth),
                    Value = if Table.RowCount(FilteredTable) > 0 then FilteredTable{0}[Value] else 0
                in
                    Value,
            
            // Base accounts (scenario-adjusted)
            BaseAccounts = GetValue("Accounts"),
            TotalAccounts = BaseAccounts * AccountMultiplier,
            
            // Account breakdown (rates not affected by scenarios)
            ActiveShare = GetValue("ActiveShare"),
            CheckingShare = GetValue("CheckingShare"),
            SavingsShare = GetValue("SavingShare"),
            
            ActiveAccounts = TotalAccounts * ActiveShare,
            CheckingAccounts = ActiveAccounts * CheckingShare,
            SavingsAccounts = ActiveAccounts * SavingsShare,
            
            // Transaction volumes (rates not affected by scenarios)
            ACHIncomingTxns = ActiveAccounts * GetValue("ACHinPerActive"),
            ACHOutgoingTxns = ActiveAccounts * GetValue("ACHoutPerActive"),
            RTPIncomingTxns = ActiveAccounts * GetValue("RTPinPerActive"),
            RTPOutgoingTxns = ActiveAccounts * GetValue("RTPoutPerActive"),
            WireIncomingTxns = ActiveAccounts * GetValue("WireInPerActive"),
            WireOutgoingTxns = ActiveAccounts * GetValue("WireOutPerActive"),
            DebitCardTxns = ActiveAccounts * GetValue("DebitCardTransactionsPerActive"),
            
            // Revenue (rates not affected by scenarios)
            ACHIncomingRevenue = ACHIncomingTxns * GetValue("ACHinRate"),
            ACHOutgoingRevenue = ACHOutgoingTxns * GetValue("ACHoutRate"),
            RTPIncomingRevenue = RTPIncomingTxns * GetValue("RTPinRate"),
            RTPOutgoingRevenue = RTPOutgoingTxns * GetValue("RTPoutRate"),
            WireIncomingRevenue = WireIncomingTxns * GetValue("WireInRate"),
            WireOutgoingRevenue = WireOutgoingTxns * GetValue("WireOutRate"),
            DebitCardRevenue = DebitCardTxns * GetValue("DebitCardTransactionRate"),
            
            TotalTransactions = ACHIncomingTxns + ACHOutgoingTxns + RTPIncomingTxns + RTPOutgoingTxns + WireIncomingTxns + WireOutgoingTxns + DebitCardTxns,
            TotalRevenue = ACHIncomingRevenue + ACHOutgoingRevenue + RTPIncomingRevenue + RTPOutgoingRevenue + WireIncomingRevenue + WireOutgoingRevenue + DebitCardRevenue,
            
            // Create record with all calculations
            CalculationRecord = [
                TotalAccounts = TotalAccounts,
                ActiveAccounts = ActiveAccounts,
                CheckingAccounts = CheckingAccounts,
                SavingsAccounts = SavingsAccounts,
                ACHIncomingTxns = ACHIncomingTxns,
                ACHOutgoingTxns = ACHOutgoingTxns,
                RTPIncomingTxns = RTPIncomingTxns,
                RTPOutgoingTxns = RTPOutgoingTxns,
                WireIncomingTxns = WireIncomingTxns,
                WireOutgoingTxns = WireOutgoingTxns,
                DebitCardTxns = DebitCardTxns,
                TotalTransactions = TotalTransactions,
                ACHIncomingRevenue = ACHIncomingRevenue,
                ACHOutgoingRevenue = ACHOutgoingRevenue,
                RTPIncomingRevenue = RTPIncomingRevenue,
                RTPOutgoingRevenue = RTPOutgoingRevenue,
                WireIncomingRevenue = WireIncomingRevenue,
                WireOutgoingRevenue = WireOutgoingRevenue,
                DebitCardRevenue = DebitCardRevenue,
                TotalRevenue = TotalRevenue,
                RevenuePerAccount = if TotalAccounts > 0 then TotalRevenue / TotalAccounts else 0
            ]
        in
            CalculationRecord
    ),
    
    // Expand the calculation record into columns
    #"Expanded Calculations" = Table.ExpandRecordColumn(#"Added Calculations", "Calculations", 
        {"TotalAccounts", "ActiveAccounts", "CheckingAccounts", "SavingsAccounts", 
         "ACHIncomingTxns", "ACHOutgoingTxns", "RTPIncomingTxns", "RTPOutgoingTxns", 
         "WireIncomingTxns", "WireOutgoingTxns", "DebitCardTxns", "TotalTransactions",
         "ACHIncomingRevenue", "ACHOutgoingRevenue", "RTPIncomingRevenue", "RTPOutgoingRevenue", 
         "WireIncomingRevenue", "WireOutgoingRevenue", "DebitCardRevenue", "TotalRevenue", "RevenuePerAccount"})
in
    #"Expanded Calculations"
```

---

## 🔧 **3. NEW PartnerTable (M Code)**

Create a PartnerTable that works with the new structure:

```m
let
    // Define partners
    Partners = Table.FromRows({
        {"PartnerFI", "Partner Financial Institution"},
        {"PhnxBank", "Phoenix Bank"},
        {"Phoenix", "Phoenix Platform"}
    }, {"PartnerCode", "PartnerName"}),
    
    // Get months
    MonthRange = List.Numbers(1, 60, 1),
    MonthTable = Table.FromList(MonthRange, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Renamed Month Column" = Table.RenameColumns(MonthTable,{{"Column1", "Month"}}),
    
    // Cross join partners and months
    CrossJoin = Table.AddColumn(#"Renamed Month Column", "Partners", each Partners),
    #"Expanded Partners" = Table.ExpandTableColumn(CrossJoin, "Partners", {"PartnerCode", "PartnerName"}, {"PartnerCode", "PartnerName"}),
    
    // Add partner-specific calculations (if needed)
    #"Added Partner Calcs" = Table.AddColumn(#"Expanded Partners", "PartnerMultiplier", each 
        // Add any partner-specific logic here
        // For now, keeping it simple
        1.0
    )
in
    #"Added Partner Calcs"
```

---

## 🚀 **Implementation Steps:**

### **Step 1: Replace InterpolatedInputs**
1. Delete existing InterpolatedInputs table
2. Create new table using the M Code above
3. Name it "InterpolatedInputs"

### **Step 2: Replace CalcsTable**
1. Delete existing CalcsTable
2. Create new table using the M Code above
3. Name it "CalcsTable"
4. **Reference the new InterpolatedInputs table** in the code

### **Step 3: Replace PartnerTable**
1. Delete existing PartnerTable (if needed)
2. Create new table using the M Code above
3. Name it "PartnerTable"

### **Step 4: Simple DAX Measures**
With the new tables, your DAX measures become very simple:

```dax
// Simple lookups from CalcsTable
TotalAccounts = 
CALCULATE(
    MAX('CalcsTable'[TotalAccounts]),
    'CalcsTable'[Month] = SELECTEDVALUE('DateTable'[Month]),
    'CalcsTable'[Scenario] = IF(ISBLANK(SELECTEDVALUE('Scenarios'[ScenarioName])), "Base", SELECTEDVALUE('Scenarios'[ScenarioName]))
)

TotalRevenue = 
CALCULATE(
    MAX('CalcsTable'[TotalRevenue]),
    'CalcsTable'[Month] = SELECTEDVALUE('DateTable'[Month]),
    'CalcsTable'[Scenario] = IF(ISBLANK(SELECTEDVALUE('Scenarios'[ScenarioName])), "Base", SELECTEDVALUE('Scenarios'[ScenarioName]))
)

// And so on for other metrics...
```

---

## ✅ **Benefits of This Approach:**

1. **Pre-calculated**: All interpolation and calculations done in M Code
2. **Scenario-correct**: Only accounts affected by scenarios
3. **Simple DAX**: Just lookups from the CalcsTable
4. **Clean structure**: Well-organized, maintainable tables
5. **Performance**: Efficient queries and calculations

---

## 🎯 **Ready to Start?**

This approach gives you:
- ✅ **Complete interpolated data** for all 60 months
- ✅ **All calculations pre-computed** for all scenarios
- ✅ **Correct scenario logic** (only accounts change)
- ✅ **Simple DAX measures** for your reports

**Would you like me to provide any additional details or modifications to this approach?**