#pragma once

#include <sstream>
#include <string>

namespace Container {
    template<typename cont_T>
    std::string print_container(const cont_T &cont, const std::string &delim = ",") {
        std::ostringstream r;
        auto i = cont.begin();
        auto e = cont.end();
        if (i == e)
            return r.str();
        r << *i++;
        for ( ; i != e; ++i)
            r << delim << *i;
        return r.str();
    }
}
