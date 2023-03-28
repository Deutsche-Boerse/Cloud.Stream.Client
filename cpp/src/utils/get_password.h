#pragma once

#include <unistd.h>
#include <termios.h>
#include <iostream>

void get_password(std::string &password)
{
    static struct termios old_terminal;
    static struct termios new_terminal;

    //get settings of the actual terminal
    tcgetattr(STDIN_FILENO, &old_terminal);

    // do not echo the characters
    new_terminal = old_terminal;
    new_terminal.c_lflag &= ~(ECHO);

    // set this as the new terminal options
    tcsetattr(STDIN_FILENO, TCSANOW, &new_terminal);

    // get the password
    // the user can add chars and delete if he puts it wrong
    // the input process is done when he hits the enter
    // the \n is stored, we replace it with \0
    std::cin >> password;

    // go back to the old settings
    tcsetattr(STDIN_FILENO, TCSANOW, &old_terminal);
}
