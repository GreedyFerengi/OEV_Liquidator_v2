from tools import *
from oev import OEV
from thegraph import fetchV2UnhealthyLoans, getLivePriceValue

class Execution:
    def __init__(self, web3, account, fl_address, minimum_bid, wrapped_token):
        self.name = self.__class__.__name__
        self.web3 = web3
        self.account = account
        self.unhealthy_loans = fetchV2UnhealthyLoans()
        self.auctions = {}

        self.wrapped_token = wrapped_token

        self.native_price = getLivePriceValue(wrapped_token, 1*10 ** 18)
        print(f"FTM price: {self.native_price}")
        self.minimum_bid = int(minimum_bid)

        fl_abi = json.loads(open('./contracts/storage/flashLoanReceiver_abi.json').read())
        self.flashloanreciver = load_contract(self.web3, fl_address, fl_abi)
        self.oev = OEV(web3)

    def update_loans(self):
        print(f'updating loan data.....')
        try:
            self.unhealthy_loans = fetchV2UnhealthyLoans()
        except:
            print(f'an error occurred, most likely an HTTP call to the subgraph. loop will continue without updated loans')
        try:
            native_price = getLivePriceValue(self.wrapped_token, 1*10 ** 18) # update execution's native network token price each loop
            if native_price != self.native_price:
                self.native_price = native_price
                print(f'native network token price updated: {self.native_price:.4f}')
                time.sleep(15)
        except:
            print(f'an error occurred, most likely an HTTP call to the pricing source. loop will continue without updating native token price')

    def place_bids(self):
        print(f'checking loans.....')
        for loan in self.unhealthy_loans:
            if loan.totalCollateralInUSD > loan.totalBorrowInUSD and loan.healthFactor / 10 ** 18 < 1.01:
                print(f'User {loan.user} liquidation possible:')
                print(f"\tCollateral Token: {loan.collateralToken}, Borrow Token: {loan.borrowToken}")
                print(f"\tLiquidation Price: {loan.liquidationPrice:.4f}, Total Collateral In USD: {loan.totalCollateralInUSD:.4f}")
                print(f"\tTotal Borrow In USD: {loan.totalBorrowInUSD:.4f}, Health Factor: {loan.healthFactor / 10 ** 18}")
                profit_potential = (loan.totalCollateralInUSD - loan.totalBorrowInUSD) - self.native_price/10 # collateral value minus borrow value minus .1 native token for gas
                if profit_potential > 0:
                    bid_amount = int((profit_potential * 0.5) / self.native_price ) # bidding half of the potential profit in native tokens for the update
                    if bid_amount < self.minimum_bid:
                        bid_amount = self.minimum_bid
                        profit_potential = profit_potential - ((self.minimum_bid/10**18)*self.native_price) # if using min bid, factor it into profit potential
                    if profit_potential > 0:
                        print(f'profit potential: {profit_potential}, bid amount: {bid_amount}')
                        bid = self.oev.place_bid(self.account, self.flashloanreciver.address, bid_amount=bid_amount, oracle_value=int(loan.liquidationPrice * 10 ** 18), dAppProxyAddress=Addresses.FTMoevDatafeedProxy)
                        print(f'bid placed: {bid}')
                        self.auctions[bid["id"]] = loan
                else:
                    print(f'the profit potential is {profit_potential} USD, no bid placed.')

    def check_winners(self):
        print(f'checking oev endpoint for auctions won.....')
        wins = self.oev.winning_bids(self.account)
        if wins:
            for auction in wins['winningBidIds']:
                loan = self.auctions[auction]
                user = loan.user
                collateral = loan.collateralToken
                reserve = loan.borrowToken
                loan_amount = 0
                for item in loan.borrowReserve:
                    if item[1] == loan.borrowToken:
                        loan_amount = int(item[2])
                encodedUpdateTransaction = wins["encodedUpdateTransaction"]
                nativeCurrencyAmount = int(wins["nativeCurrencyAmount"])
                args = ([Addresses.Api3ServerV1], [encodedUpdateTransaction], [nativeCurrencyAmount], [reserve], [loan_amount], [0], collateral + user.replace("0x", ""))
                function = self.flashloanreciver.functions.doLiquidation(*args)
                tx_params = get_tx_params(web3=web3, account=self.account, value=nativeCurrencyAmount, gas=1000000)
                tx = build_and_send_and_wait(web3, self.account, function, tx_params)
                print(f'price update and liquidation multicall submitted: {tx}')


async def update_loans(executor):
    print(f'starting loop to keep loan database updated.....')
    time.sleep(180)
    while True:
        executor.update_loans()

async def bidder_loop(executor):
    print(f'starting loop to place bids if an opportunity is found.....')
    while True:
        executor.place_bids()
        time.sleep(30)

async def settlement_loop(executor):
    print(f'starting loop to settle any possible liquidations.....')
    while True:
        executor.check_winners()
        time.sleep(30)

if __name__ == "__main__":
    web3 = Web3(HTTPProvider(endpoint_uri=os.getenv("RPC"), request_kwargs={'timeout': 100}))
    account = web3.eth.account.from_key(os.getenv("PRIV_KEY"))
    executor = Execution(web3, account, os.getenv("FL_ADDRESS"), os.getenv("MIN_BID"), os.getenv("WRAPPED_NETWORK_TOKEN"))

    def first_thread_tasks():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(update_loans(executor))
        loop.run_forever()
    t1 = Thread(target=first_thread_tasks)
    t1.start()

    def second_thread_tasks():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(bidder_loop(executor))
        loop.run_forever()
    t2 = Thread(target=second_thread_tasks)
    t2.start()

    def third_thread_tasks():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(settlement_loop(executor))
        loop.run_forever()
    t2 = Thread(target=third_thread_tasks)
    t2.start()
