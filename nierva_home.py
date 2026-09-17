import streamlit as st

def main():
    st.markdown(
        '''
        <h1 align="center"> Unnamed Educational Minigame Prototype 🎮 </h1>
        #### Overview 

        
        DISCLAIMER [!!!] : This AI-Assisted project contains fixes and improvements MADE BY AI ( Github Copilot ). 

        
        Welcome, this project is a prototype model the [ Unnamed Educational Minigame ].
        This web application serves as a rough framework of "minigames" prior to the final
        changes that will become its own unique educational / informational variants. 
        
        So for now, I will only go as far as to cover a few of the core mechanics I'm going for with
        this current patch. Sooner or later, I plan on adding a few more minigames and I will soon be
        remastering this project wiht MY OWN WRITTEN CODE.

        This application is currently built with Python using Streamlit, through the Github
        Codespace for development.
        
        Current active minigames include [ Final output will vary ] :

        1. Slider Minigame - This minigame presents a sliders, each one with a marker 
                             moving over choices, the player must stop the marker on the 
                             correct choice to complete the slider.
        2. Bit Fit Minigame - This minigame presents a set of columns that contain multiple answers 
                             to a question. The player must be able cycle through and match all the 
                             correct answers within the time limit. The more you complete, the 
                             harder the each round becomes. 
        3. Terminal Hacking - This minigame presents a block of hashed text with words hidden
                              all throughout, one of which contains the answer to the question.
                              Each word the player guesses will appear in the guess log to the 
                              right side.

        NOTE: The current state of the project is still in development, so the minigames shown are currently 
                          available are subject to distinct changes that stray away from the inspired
                          gameplay mechanics.
        ''',
        unsafe_allow_html=True,
    )

if __name__ == '__main__':
    main()
