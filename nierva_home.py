import streamlit as st

def main():
    st.markdown(
        '''
        <h1 align="center"> Unnamed Educational Minigame Prototype 🎮 </h1>
        ---
        #### Overview

        Welcome, this project is a prototype model the [ Unnamed Educational Minigame ].
        This web application serves as a rough framework of "minigames" prior to the final
        changes that will become its own unique educational / informational variants. So for
        now, I will only go as far as to implement the core mechanics for this patch.

        This application is currently built with Python using Streamlit, through the Github
        Codespace for development.
        
        Current active minigames include [ Final output will vary ] :

        1. Slider Minigame - A timing and precision mechanics test where players stop a moving
                             marker within target sections
        2. Bit Fit Minigame - A binary pattern-matching game where players toggle bit registers
                              to align with falling bit streams.
        3. Terminal Hacking - A logic and deduction puzzle where players locate decrypted texts
                              terminals using positional feedback symbols.

        Select a minigame module from the sidebar navigation to test its core functionality.
        ''',
        unsafe_allow_html=True,
    )

if __name__ == '__main__':
    main()
