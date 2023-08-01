import requests, json, time
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class Loan:
    user: str
    collateralToken: str
    borrowToken: str
    liquidationPrice: Decimal
    totalCollateralInUSD: Decimal
    totalBorrowInUSD: Decimal
    healthFactor: Decimal
    collateralReserve: list
    borrowReserve: list

def fetchV2UnhealthyLoans(theGraphURL="https://api.thegraph.com/subgraphs/name/0xfantommenace/granary-api3"):
    headers = {"Content-Type": "application/json"}

    query = """
    query {
      users(
        first: 1000
        skip: 0
        orderBy: id
        orderDirection: desc
        where: {borrowedReservesCount_gt: 0}
      ) {
        id
        borrowedReservesCount
        collateralReserve: reserves(where: {currentATokenBalance_gt: 0}) {
          currentATokenBalance
          reserve {
            usageAsCollateralEnabled
            reserveLiquidationThreshold
            reserveLiquidationBonus
            borrowingEnabled
            utilizationRate
            symbol
            underlyingAsset
            price {
              priceInEth
            }
            decimals
          }
        }
        borrowReserve: reserves(where: {currentTotalDebt_gt: 0}) {
          currentTotalDebt
          reserve {
            usageAsCollateralEnabled
            reserveLiquidationThreshold
            borrowingEnabled
            utilizationRate
            symbol
            underlyingAsset
            price {
              priceInEth
            }
            decimals
          }
        }
      }
    }
    """

    response = requests.post(theGraphURL, headers=headers, json={"query": query})
    loansJson = response.json()

    loans = []
    local_price_storage = {}
    for user in loansJson["data"]["users"]:
        collateralReserve = []
        for reserve in user["collateralReserve"]:
            token = reserve["reserve"]["underlyingAsset"]
            amount = reserve["currentATokenBalance"]
            if token in local_price_storage.keys():
                amountInUSD = getStoredPriceValue(token, amount, local_price_storage[token])
            else:
                amountInUSD = getLivePriceValue(token, amount)  # Implement getAssetPrice function
                local_price_storage[token] = amountInUSD / int(amount)
            collateralReserve.append((reserve["reserve"]["symbol"], token, amount, amountInUSD))

        borrowReserve = []
        for reserve in user["borrowReserve"]:
            token = reserve["reserve"]["underlyingAsset"]
            amount = reserve["currentTotalDebt"]
            if token in local_price_storage.keys():
                amountInUSD = getStoredPriceValue(token, amount, local_price_storage[token])
            else:
                amountInUSD = getLivePriceValue(token, amount)  # Implement getAssetPrice function
                local_price_storage[token] = amountInUSD / int(amount)
            borrowReserve.append((reserve["reserve"]["symbol"], token, amount, amountInUSD))

        try:
            totalCollateralInUSD = sum(amountInUSD for _, _, _, amountInUSD in collateralReserve)
            totalBorrowInUSD = sum(amountInUSD for _, _, _, amountInUSD in borrowReserve)
            healthFactor = (totalCollateralInUSD * 85 * (10 ** 18)) / (totalBorrowInUSD * 100)

            loans.append(
                Loan(
                    user=user["id"],
                    collateralReserve=collateralReserve,
                    borrowReserve=borrowReserve,
                    totalCollateralInUSD=totalCollateralInUSD,
                    totalBorrowInUSD=totalBorrowInUSD,
                    healthFactor=healthFactor,
                    borrowToken=None,
                    collateralToken=None,
                    liquidationPrice=None
                )
            )
        except:
            pass

    unhealthyLoans = [loan for loan in loans if loan.healthFactor < (10 ** 18) * 12 / 10]
    unhealthyLoansFiltered = [loan for loan in unhealthyLoans if len(loan.collateralReserve) == 1 and len(loan.borrowReserve) == 1]

    liquidationPrices = []
    for loan in unhealthyLoansFiltered:
            collateralToken = loan.collateralReserve[0][1]
            borrowToken = loan.borrowReserve[0][1]
            liquidationPrice = (loan.totalBorrowInUSD * (10 ** 18) * 100) / (85 * int(loan.collateralReserve[0][2]))
            hf = ('{:.0f}'.format(loan.healthFactor))
            liquidationPrices.append(
                Loan(
                    user=loan.user,
                    collateralToken=collateralToken,
                    borrowToken=borrowToken,
                    collateralReserve=loan.collateralReserve,
                    borrowReserve=loan.borrowReserve,
                    liquidationPrice=liquidationPrice,
                    totalCollateralInUSD=loan.totalCollateralInUSD,
                    totalBorrowInUSD=loan.totalBorrowInUSD,
                    healthFactor=float(hf),
                )
            )
    if liquidationPrices:
        # print(liquidationPrices)
        return liquidationPrices

def getTokenValues(token: str):
    name = None
    decimal = None
    if token == '0x21be370d5312f44cb42ce377bc9b8a0cef1a4c83':
        name = 'wrapped-fantom'
        decimal = 18
    if token == '0x74b23882a30290451a17c44f4f05243b6b58c76d':
        name = 'ethereum'
        decimal = 18
    if token == '0x04068da6c83afcfa0e13ba15a6696662335d5b75':
        name = 'usd-coin'
        decimal = 6
    return name, decimal

def getStoredPriceValue(token: str, amount: Decimal, price) -> Decimal:
    name, decimal = getTokenValues(token)
    return price * (int(amount) / 10 ** decimal)

def getLivePriceValue(token: str, amount: Decimal) -> Decimal:
    name, decimal = getTokenValues(token)
    url = "https://api.coingecko.com/api/v3/coins/" + name
    response = requests.get(url).text
    data = json.loads(response)
    time.sleep(1)
    try:
        return data['market_data']['current_price']['usd'] * (int(amount) / 10 ** decimal)
    except KeyError:
        time.sleep(60)
        response = requests.get(url).text
        data = json.loads(response)
        print(f"2nd try price: {data['market_data']['current_price']['usd']}")
        return data['market_data']['current_price']['usd'] * (int(amount) / 10 ** decimal)

if __name__ == "__main__":
    loans = fetchV2UnhealthyLoans()
    for loan in loans:
        print(f"User: {loan.user}:")
        print(f" \t Collateral Token: {loan.collateralToken}, Borrow Token: {loan.borrowToken}")
        print(f" \t Liquidation Price: {loan.liquidationPrice:.4f}, Total Collateral In USD: {loan.totalCollateralInUSD:.4f}")
        print(f" \t Total Borrow In USD: {loan.totalBorrowInUSD:.4f}, Health Factor: {loan.healthFactor/10**18}")

