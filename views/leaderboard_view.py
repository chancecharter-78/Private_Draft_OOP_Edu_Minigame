import streamlit as st

from nierva_save_data import get_leaderboard


def main():
    st.title("🏆 Shared Leaderboard")
    st.caption("Scores are stored in the shared Supabase database.")

    players = get_leaderboard(limit=100)
    if players:
        st.dataframe(players, hide_index=True, width="stretch")
    else:
        st.info("No players have been added to the leaderboard yet.")


if __name__ == "__main__":
    main()
