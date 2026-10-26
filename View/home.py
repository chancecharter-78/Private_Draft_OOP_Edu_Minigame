import streamlit as st

from Controller.player import reset_save_data


@st.dialog("Reset save progress?")
def confirm_reset_save_data():
    st.warning(
        "This will reset your points, rank progress, successful-round count, "
        "and clear history. Your account, servers, question sets, and review "
        "schedules will not be deleted."
    )
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key="cancel_reset_save_data"):
            st.session_state.reset_confirmation_open = False
            st.rerun()
    with confirm_col:
        if st.button(
            "Reset progress",
            key="confirm_reset_save_data",
            type="primary",
        ):
            reset_save_data()
            st.session_state.reset_confirmation_open = False
            st.rerun()


def main():
    st.markdown(
        """
        # Voiding Boredom Alpha V3 🎮
        Overview

        DISCLAIMER [!!!] : This AI-Assisted project contains fixes and improvements MADE BY AI ( Github Copilot ).

        Welcome, this project is a prototype model the Voiding Boredom V3 Alpha Unstable.
        This web application serves as a rough framework of "minigames" prior to the final
        changes that will become its own unique educational / informational variants.

        So for now, I will only go as far as to cover a few of the core mechanics I'm going for with
        this current patch. Sooner or later, I plan on adding a few more minigames and I will soon be
        remastering this project wiht MY OWN WRITTEN CODE.

        This application is currently built with Python using Streamlit, through the Github
        Codespace for development.

        This application will directly cycle between the 3 games after a sufficient amount of success,
        but the user may choose which minigame can be the starting minigame, but when entering the
        servers page, the default will be the Slider Minigame.

        Current active minigames include [ Final output will vary ] :

        1. Slider Minigame - This minigame presents a sliders, each one with a marker
                             moving over 4 choices, the player must stop the marker on the
                             correct choice to complete the slider. This can last about 2-6 rounds
                             before switching to a different minigame.
        2. Bit Fit Minigame - This minigame presents a set of columns that contain multiple answers
                             to a question. The player must be able cycle through and match all the
                             correct letters to form the word answer. The more
                             you complete, the harder the each round becomes. This can last about 5-8
                             rounds before switching to a different minigame.
        3. Terminal Hacking - This minigame presents a block of hashed text with words hidden
                              all throughout, one of which contains the answer to the question.
                              Each word the player guesses will appear in the guess log to the
                              right side. This can last about 4-6 rounds before switching to a
                              different minigame.

        NOTE: The current state of the project is still in development, so the minigames shown are currently
                          available are subject to distinct changes that stray away from the inspired
                          gameplay mechanics.
        """
    )
    save_data = st.session_state.save_data
    st.subheader("📊 Save Progress Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Player", save_data.player_name)
    col2.metric("Points", save_data.check_score())
    rank_progress = save_data.get_rank_progress()
    col3.metric("Rank", rank_progress["rank"])
    col4.metric("Total Successful Rounds", save_data.check_completed_rounds())
    st.progress(
        rank_progress["current_xp"] / rank_progress["required_xp"],
        text=(
            f"Rank {rank_progress['rank']} progress: "
            f"{rank_progress['current_xp']} / {rank_progress['required_xp']} XP"
        ),
    )
    if st.button("🔄 Reset Save Data Progress"):
        st.session_state.reset_confirmation_open = True
    if st.session_state.get("reset_confirmation_open", False):
        confirm_reset_save_data()
    if st.session_state.pop("save_reset_notice", False):
        st.success("Save progress reset.")

if __name__ == "__main__":
    main()
