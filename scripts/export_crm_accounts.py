from pathlib import Path

from app.integrations.crm_client import CRMClient
import pandas as pd


def main() -> None:
    accounts = CRMClient().fetch_accounts()
    df = pd.json_normalize(accounts)
    output_path = Path(r"C:\Projects\bellhaven-sync\bellhaven-sync\data\crm_accounts.xlsx")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    print(len(df))
    print(str(output_path.resolve()))


if __name__ == "__main__":
    main()
