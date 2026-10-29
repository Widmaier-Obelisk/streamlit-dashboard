import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from data.letterboxd import load_activity
from data.financial import load_balances, load_display_accounts

st.set_page_config(
    page_title="Data Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("Data Dashboard")
st.caption("A personal dashboard for aggregating important and interesting data.")

st.header("Financial Overview")

try:
    finances = load_balances()
    display_accounts = load_display_accounts()
    finances = finances[finances["id"].isin(display_accounts)]

    if finances.empty:
        st.warning("No financial accounts found.")
    else:
        assets = finances.loc[finances["balance"] > 0, "balance"].sum()

        liabilities = -finances.loc[finances["balance"] < 0, "balance"].sum()

        net_position = assets - liabilities

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Assets", f"${assets:,.2f}")
        col2.metric("Total Liabilities", f"${liabilities:,.2f}")
        col3.metric("Net Position", f"${net_position:,.2f}")

        st.subheader("Accounts")

        display_finances = finances[["name", "balance", "currency"]].copy()
        display_finances["balance"] = display_finances.apply(
            lambda row: f"{row['balance']:,.2f} {row['currency']}",
            axis=1,
        )

        st.dataframe(
            display_finances,
            use_container_width=True,
            hide_index=True,
        )

except (FileNotFoundError, ValueError, OSError) as exc:
    st.error(f"Unable to load financial data: {exc}")
except Exception as exc:
    st.error(f"Unexpected financial data error: {exc}")

@st.fragment(run_every=30)
def letterboxd_section() -> None:
    st.divider()

    try:
        df = load_activity()
    except (FileNotFoundError, ValueError, OSError) as exc:
        st.error(f"Unable to load Letterboxd data: {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"Unable to parse the data file: {exc}")
        st.stop()

    data_path = Path(os.getenv("LETTERBOXD_DATA_PATH", "sample_data/activity.json"))
    st.caption(f"Source: {data_path} · Updated: {datetime.fromtimestamp(data_path.stat().st_mtime).isoformat(timespec='seconds')}")

    if df.empty:
        st.warning("The activity file contains no records.")
        st.stop()

    title_col = next(
        (col for col in ["title", "film_title", "name"] if col in df.columns),
        None,
    )
    rating_col = next(
        (col for col in ["rating", "user_rating"] if col in df.columns),
        None,
    )
    date_col = next(
        (col for col in ["date", "watched_at", "created_at"] if col in df.columns),
        None,
    )

    if title_col is None:
        st.warning("Couldn't identify a film title column.")
        st.write("Available columns:", list(df.columns))
        st.dataframe(df, use_container_width=True)
        st.stop()

    if rating_col:
        df[rating_col] = pd.to_numeric(df[rating_col], errors="coerce")

    total_records = len(df)
    rated_records = int(df[rating_col].notna().sum()) if rating_col else 0
    average_rating = df[rating_col].mean() if rated_records else None

    col1, col2, col3 = st.columns(3)

    col1.metric("Activity records", total_records)
    col2.metric("Rated records", rated_records)
    col3.metric(
        "Average rating",
        f"{average_rating:.2f} / 5" if average_rating is not None else "N/A",
    )

    if rating_col and rated_records:
        st.subheader("Rating distribution")
        ratings = df[rating_col].dropna().value_counts().sort_index()
        st.bar_chart(ratings)

    st.subheader("Recent activity")

    display_df = df.copy()

    if date_col:
        display_df[date_col] = pd.to_datetime(
            display_df[date_col],
            errors="coerce",
        )
        display_df = display_df.sort_values(
            date_col,
            ascending=False,
            na_position="last",
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


letterboxd_section()
