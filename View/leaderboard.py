import streamlit as st

from Controller.player import get_leaderboard


def main():
    st.title("🏆 Online Leaderboard")

    players = get_leaderboard(limit=100)
    if players:
        st.dataframe(players, hide_index=True, width="stretch")
    else:
        st.info("No players have been added to the leaderboard yet.")


if __name__ == "__main__":
    main()
