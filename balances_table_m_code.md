# BalancesTable - Non-Recursive Balance Calculations

## 🎯 **BalancesTable Structure**

This table calculates running balances by leveraging the CalculationsTable and using cumulative logic instead of recursion.

```m
let
    // Step 1: Get base data from CalculationsTable
    BaseData = CalculationsTable,
    
    // Step 2: Get CheckingUsageRate from InterpolatedInputs
    CheckingUsageRate = try Table.SelectRows(InterpolatedInputs, each [InputType] = "CheckingUsageRate"){0}[Value] otherwise 0.8,
    SavingsUsageRate = try Table.SelectRows(InterpolatedInputs, each [InputType] = "SavingsUsageRate"){0}[Value] otherwise 0.9,
    
    // Step 3: Add usage rates to base data
    #"Added Usage Rates" = Table.AddColumn(BaseData, "CheckingUsageRate", each CheckingUsageRate),
    #"Added Savings Usage Rate" = Table.AddColumn(#"Added Usage Rates", "SavingsUsageRate", each SavingsUsageRate),
    
    // Step 4: Group by scenario to calculate balances within each scenario
    #"Grouped by Scenario" = Table.Group(#"Added Savings Usage Rate", {"ScenarioName"}, {
        {"ScenarioData", each _, type table}
    }),
    
    // Step 5: Calculate balances for each scenario
    #"Added Balance Calculations" = Table.AddColumn(#"Grouped by Scenario", "WithBalances", each
        let
            ScenarioTable = [ScenarioData],
            SortedByMonth = Table.Sort(ScenarioTable, {{"Month", Order.Ascending}}),
            
            // Add index for easier referencing
            #"Added Index" = Table.AddIndexColumn(SortedByMonth, "Index", 0),
            
            // Calculate Checking Balance using cumulative logic
            #"Added Checking Balance" = Table.AddColumn(#"Added Index", "Checking_Balance", each
                let
                    CurrentMonth = [Month],
                    CurrentIndex = [Index],
                    CurrentMonthlyChecking = [Monthly_Checking],
                    UsageRate = [CheckingUsageRate]
                in
                    if CurrentMonth = 1 then
                        // Month 1: Just the monthly checking amount
                        CurrentMonthlyChecking
                    else if CurrentMonth = 2 then
                        // Month 2: Previous month * usage rate + current month
                        let
                            Month1Row = Table.SelectRows(#"Added Index", each [Month] = 1){0},
                            Month1Checking = Month1Row[Monthly_Checking]
                        in
                            Month1Checking * UsageRate + CurrentMonthlyChecking
                    else
                        // Month 3+: Complex formula
                        let
                            PrevMonthRow = Table.SelectRows(#"Added Index", each [Index] = CurrentIndex - 1){0},
                            PrevBalance = try PrevMonthRow[Checking_Balance] otherwise 0,
                            Month1Row = Table.SelectRows(#"Added Index", each [Month] = 1){0},
                            Month1Checking = Month1Row[Monthly_Checking]
                        in
                            (PrevBalance * UsageRate - Month1Checking * UsageRate) + CurrentMonthlyChecking
            ),
            
            // Calculate Savings Balance using similar logic
            #"Added Savings Balance" = Table.AddColumn(#"Added Checking Balance", "Savings_Balance", each
                let
                    CurrentMonth = [Month],
                    CurrentIndex = [Index],
                    CurrentMonthlySavings = [Monthly_Savings_Transfers],
                    UsageRate = [SavingsUsageRate]
                in
                    if CurrentMonth = 1 then
                        // Month 1: Just the monthly savings amount
                        CurrentMonthlySavings
                    else if CurrentMonth = 2 then
                        // Month 2: Previous month * usage rate + current month
                        let
                            Month1Row = Table.SelectRows(#"Added Checking Balance", each [Month] = 1){0},
                            Month1Savings = Month1Row[Monthly_Savings_Transfers]
                        in
                            Month1Savings * UsageRate + CurrentMonthlySavings
                    else
                        // Month 3+: Complex formula
                        let
                            PrevMonthRow = Table.SelectRows(#"Added Checking Balance", each [Index] = CurrentIndex - 1){0},
                            PrevBalance = try PrevMonthRow[Savings_Balance] otherwise 0,
                            Month1Row = Table.SelectRows(#"Added Checking Balance", each [Month] = 1){0},
                            Month1Savings = Month1Row[Monthly_Savings_Transfers]
                        in
                            (PrevBalance * UsageRate - Month1Savings * UsageRate) + CurrentMonthlySavings
            ),
            
            // Calculate Total Balances
            #"Added Total Balance" = Table.AddColumn(#"Added Savings Balance", "Total_Balance", each
                [Checking_Balance] + [Savings_Balance]
            ),
            
            // Remove the index column as it's no longer needed
            #"Removed Index" = Table.RemoveColumns(#"Added Total Balance", {"Index"})
        in
            #"Removed Index"
    ),
    
    // Step 6: Expand the balance calculations back to flat table
    #"Expanded Balance Data" = Table.ExpandTableColumn(#"Added Balance Calculations", "WithBalances", 
        Table.ColumnNames(#"Added Balance Calculations"[WithBalances]{0})),
    
    // Step 7: Remove the intermediate columns
    #"Removed Scenario Data" = Table.RemoveColumns(#"Expanded Balance Data", {"ScenarioData"}),
    
    // Step 8: Set proper data types
    #"Changed Types" = Table.TransformColumnTypes(#"Removed Scenario Data",{
        {"Month", Int64.Type},
        {"Checking_Balance", type number},
        {"Savings_Balance", type number},
        {"Total_Balance", type number},
        {"CheckingUsageRate", type number},
        {"SavingsUsageRate", type number}
    })
    
in
    #"Changed Types"
```

## 🧠 **How This Works Without Recursion:**

### **Key Insight: Group by Scenario**
1. **Group table by scenario** - each scenario gets its own subtable
2. **Sort by month** within each scenario
3. **Add index** for easy referencing of previous rows
4. **Calculate balances** using previous row references instead of recursion

### **Balance Logic Implemented:**
1. **Month 1**: `Balance = Monthly_Flow`
2. **Month 2**: `Balance = Month1_Flow * UsageRate + Month2_Flow`  
3. **Month 3+**: `Balance = (PrevBalance * UsageRate - Month1_Flow * UsageRate) + CurrentFlow`

### **Why This Works:**
- ✅ **No recursion** - uses table lookups instead
- ✅ **Handles dependencies** - previous month references work
- ✅ **Scenario isolation** - each scenario calculated independently  
- ✅ **Performance** - pre-calculated for all scenarios

## 🚀 **Implementation Plan:**

1. **First**: Test basic CalculationsTable structure
2. **Then**: Add this BalancesTable 
3. **Finally**: Create simple DAX measures to pull from both tables

**Ready to start with the CalculationsTable?**