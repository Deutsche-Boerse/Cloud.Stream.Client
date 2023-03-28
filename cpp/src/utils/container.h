#pragma once

#include <array>
#include <deque>
#include <list>
#include <vector>

#include <sstream>

namespace Container {
    template<typename cont_T>
    std::string print_container(const cont_T &cont, const std::string &delim = ",") {
        std::stringstream res;
        for (const auto &elem: cont) {
            res << elem;
            if (elem != cont.back()) res << delim;
        }
        return res.str();
    }
}