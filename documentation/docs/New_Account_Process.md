Process of making a new account and then taking it from a PUA to a FUA. (new account control flow process)

1. Steamgaurd is put onto the new account using steamguard.py which also reads it into the database.

2. The Prime activation and Armoury activation process take place.

3. Once the account has at least prime, farming will begin on it.

4. Eventually more and more armoury passes will be purchased on this account and it will reach the FUA status.

5. Then, this account will join the existing FUA accounts (if any) and a new account will undergo this entire process.

Prime Activation:

1. When all accounts are fully upgraded and you need to make new prime account(s) (Note: In the long run if you are making multiple fully upgraded accounts at once, the corresponding amount needed for steamgiftcards will be sent to main account to sell on third party) predict the future price and transfer the corresponding amount of items to main account and then wait 10 days.

After doing this send out the items to the accounts in an account by account process where you go to the next account once the current account has enough items to be fully upgraded.

Price prediction using: (estimated selling price of the cases on third party are 10 days out price which is considered safe. Selling price of cases on steam are calculated as a very safe maximum average selling price based on expected range to exist from 7 days to 10 days out (usually just 1.2-1.3x of the needed price is transferred (if u need to transfer 100, you transfer 125))). (Note: this step is optional if existing cash reserves are enough to cover the giftcard expenses)

2. After 10 days, list the third party allocated cases on third party using api.

3. Sell the third party items and withdraw the balance. (automation later)

4. Buy balance on moogold and redeem giftcards. (done in a batched process, refer to Giftcard redeemer) (automate later)

5. Use the giftcards, account by account getting each to $5.
   Here, youve already waited for 10 days so the inventory items are already marketable.

6. Sell the items and buy prime and up to 5 passes (as many as possible) while doing this, update the database tags.

Usage: 

Now that you have switched fully to crypto by selling drops to crypto and withdrawing the crypto and buying giftcards with crypto, only notifications will be sent and no intervention is necessary.

Armoury Pass Activation:

1. The FUA accounts are constantly running their item listers and botlooter trader, sending excees items to the new account.

2. When a new account receives an item, its marketability time is noted in the new items table in the database.
When an item becomes marketable, the items lister is automatically run on the PUA, selling all items.

3. If there is enough wallet balance to buy an armoury pass, the armoury pass buyer is used to buy the pass and the database is updated.