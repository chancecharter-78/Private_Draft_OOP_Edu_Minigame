import streamlit as st

from nierva_save_data import get_leaderboard


def reset_save_data():
    st.session_state.save_data.reset_save()
    st.session_state.save_reset_notice = True


def main():
    st.markdown(
        """
        # Unnamed Educational Minigame Prototype 🎮
        Overview

        DISCLAIMER [!!!] : This AI-Assisted project contains fixes and improvements MADE BY AI ( Github Copilot ).

        Welcome, this project is a prototype model the [ Unnamed Educational Minigame ].
        This web application serves as a rough framework of "minigames" prior to the final
        changes that will become its own unique educational / informational variants.

        So for now, I will only go as far as to cover a few of the core mechanics I'm going for with
        this current patch. Sooner or later, I plan on adding a few more minigames and I will soon be
        remastering this project wiht MY OWN WRITTEN CODE.

        This application is currently built with Python using Streamlit, through the Github
        Codespace for development.

        This application will directly cycle between the 3 games after a sufficient amount of success,
        but the user may choose which minigame can be the starting minigame, but when entering the
        minigames section, the default will be the Slider Minigame.

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
    col2.metric("Accumulated Score", save_data.check_score())
    col3.metric("Player Level", save_data.check_level())
    col4.metric("Total Clears", save_data.check_completed_rounds())

    st.button("🔄 Reset Save Data Progress", on_click=reset_save_data)
    if st.session_state.pop("save_reset_notice", False):
        st.success("Save Data reset back to initial Set 1 state!")

    st.subheader("🏆 Local Leaderboard")
    leaderboard = get_leaderboard()
    if leaderboard:
        st.dataframe(leaderboard, hide_index=True, width="stretch")
    else:
        st.info("No players have been added to the leaderboard yet.")


if __name__ == "__main__":
    main()
