A guide to the daily processes of existing accounts for efficient operation of the farm. (existing accounts control flow process)

Account Types:

PUA: Partially upgraded account (This type of account needs more armoury passes to become farmable 24/7)
FUA: Fully upgraded account (This type of account has all the armoruy passes and can be farmed 24/7)
At one time there is only 1 PUA account.


Scheduler usage:

0. Run the stage_0.py if running in fully automated manner

1. If not fully automated, skip stage_0 and run stage_1 at night before sleeping

2. After running stage_1, for the accounts that show up in the farm list in TickTick, buy armoury passes and activate them, then create FarmLabs armoury pass farm jobs for them (if such jobs dont exist yet, just create regular farm jobs till level 40 and keep monitoring the account till it reaches 200 stars, then cancel the job). When jobs are created and when a job reaces "in progress" state in FarmLabs, update it correspondingly in TickTick in the farm list.

3. After the farm job completes for an account, close the finished passes and then run the redemption_reccomender (it can be run directly from accounts manager utils and also available as stage 2 in scheduler(recommended)). Redeem the recommended armoury pass items on all accounts that have finished pass farming and make the update in the TickTick farm list.