# OEV_Liquidator_v2 a Granary Finance liquidator bot for auctions using API3 OEV

This bot for Granary Finance will monitor open loans via the graph and submit OEV bids to update the price and liquidate!

1. Copy the env file to .env and fill out all the necessary information within it
2. Run the deployer.py script to deploy the smart contract
3. Go to the https://oev.api3.org/ frontend and deposit into the OEV Prepayment Depository
4. Run the smart contract unit tests to ensure .env params are correct and the contract functions complete
   - ensure there's about 100 FTM in your wallet, the tests will do some swaps for USDC and add to the smart contract so it can test swaps and flash loans, then it will withdraw it.
   - Run unit_tests.py
5. Ensure the flash loan transaction completed, as well as the oev price updated tranasaction. Successful unit tests will look like as follows:

7. Run the bot using execution.py


Due to the Multichain hack and the depletion of asset backing on Fantom, there have been limited opportunities to test this bot. A testnet setup is currently in development to validate it's efficacy. However, at the current time, the on-chain liquidation portion is largely untested. 
