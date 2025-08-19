FARM manager

New Account manager:

Pipeline:

1. Steamgaurd adder (steamguardAdder module)

2. a code to calculate how much to be traded to third party account (do 1.5x of current buy order prices) and then rest to the new account(s), it has a gui and shows the trade and asks for final  confirmation and then makes the trades (called Trader.py). You can select how many accounts u want, if more than 1 it checks if enough to send to each account ennough items for prime + all armoury passes if not it sends to the max number of accounts where that is possible or just 1 account. (can be set to autoaccept) 

3. Wait 7 days if enough balance on moogold else: notify user to either add balance or make the delay 10.5 days upon which balance is checked again (user can keep delaying by set number of hours as per need) when enough balance, step 4 is triggered

4. giftcard buyer and redeemer (eventually fully automated, rn balance on moogold needs to be added manually)

5. items lister reused (0 passes args used)

6. prime purchaser (db also updated)

7. Set this new account to the current PUA (Partiallu upgraded account) in the db while ensuring that all others are fully upgraded

(NewAccount Pipeline, mostly automated, can become fully automated)


Existing Accounts manager: 

Runs steam items lister and then botlooter trader on all accounts with armoury pass every time a batch of items become tradable/marketable. Here if new account must be made (all existing have armoury passes filled) then NewAccountTrader is run instead of these 2. (ArmouryMarketProcess)

Armoury pass progress checker is continuously running on all accounts being active farmed (checks every 10 minutes) by sending a request to the corresponding client which then responds with the number of stars.

Whenever pass progress checker indicates that pass is completed then pass redeemer is run. Once the redeemer is run it sets num active passes to 0 and then occasionally checks for sufficient wallet balance and then pass buyer is run and then the number of total passes and current active passes (incomplete) are updated which triggers panel (panel also informs checker once that starts).

Whenever an item is received, update its next items become marketable time, at that time the items lister are run automatically and botlooter trader if its not the pua

Redemption reccomender (recommends which item to redeem to the redeemer) (has a gui for user to access) (armoury stars processes)

Panel:

View: For now it just takes you to dashboard.farmlabs.dev in chrome. Eventually takes you to own custom panel when implemented.

Constant database watcher thata waits for updates and runs the below on update:
1. If a new account has prime and at least 1 active armoury pass it is added to the regular pool of accounts.

2. For the regular accounts pool whenever an account has no active armoury passes, its job is cancelled and deleted. When it has passes again (FUA need 5 active to restart and PUA need at least 1 to restart) then the job is recreated (here bot job is a clara mode xp bot that switches to dust 2 and normal during periods of low traffic). The armoury stars process closes farmlabs and reopens it after its work is done and so has no affect on this.

3. Case drops redeemer that redeems drops based on best price

third party marketplace:

1. A Process that keeps waiting for sales to occur and upon receiving a trade request uses the third party api to check its legitimacy and then it confirms the trade request. (forever running server process) (Trade acceptor process)

2. code to list items for sale on third party. it gets the list of items to sell as args or from temp file which is passed as an argument and then lists those competitively (either lowest price or matching price if only a few exist at that price (use fractions to determine this)). advanced feature is checking every few minutes to ensure that prices are competitive and if not lowers them.
(continuously running third party listing package)

3. A utility that tells the current value of all items if sold on third party (util)

Major modules: new_accounts_pipeline, accounts_manager, panel, third party

Clients:

PC client: 

Serves as the pc client of the Farm manager. Receives cs2 application commands like:
1. redeem case drops
2. buy armoury pass
3. redeem aromoury stars
4. Check armoury pass number of stars
5. Farming config (VMs list in case of farmlabs or accounts list in case of own panel)
For tasks 1 to 3, it launches a VM and passes these to the VM client. For task 4 it gets the corrospodning VM and then passes it to the checker within the running VM(if using farmlabs, else just pass it to the own panel which just updates the db automatically) For task 5, if using farmlabs, it launches the corresponding VMs. If using own panel, it passes the accounts list to the farming panel which takes care of the rest.

VM client:

For tasks 1 to 3 it simply closes any running farmlabs or cs2 and restarts cs2 and steam.
For task 4 it simply allows everything to run and checks the num stars whil farmlabs is running.

Botlooter:

Receives a request to send out trades with a list of accounts passed to it. It also has the ability to autoaccept on the reciviver side using aiosteampy.

Top level folders:

database
new_accounts_pipeline
accounts_manager (for existing accounts)
Panel
third party
pc_client
vm_client
Botlooter
utils (only contains shared utils)
documentation
manager
top level files: .md files, zzz_test.py, requirements.txt 

Eventually:

Disable the new account process on the armoury pass side and add a Case farm side that is separate once stage 1 is complete in 2 years