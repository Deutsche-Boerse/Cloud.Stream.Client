#pragma once

#include <sys/wait.h>
#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <string>
#include <vector>

namespace OSCommandExecuter {
    std::string execute(std::string cmd) {
        std::array<char, 128> buffer;
        std::string result;
        std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
        if (!pipe) {
            throw std::runtime_error("popen() failed!");
        }
        while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
            result += buffer.data();
        }
        return result;
    }
}