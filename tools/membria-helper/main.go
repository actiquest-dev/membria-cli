package main

import (
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"strings"
)

func main() {
	if len(os.Args) < 2 {
		return
	}
	u, err := url.Parse(os.Args[1])
	if err != nil {
		return
	}
	if u.Scheme != "membria" {
		return
	}
	cmd := u.Query().Get("cmd")
	cmd = strings.TrimSpace(cmd)
	if cmd == "" {
		return
	}
	// Open Terminal and run command
	script := fmt.Sprintf("tell application \"Terminal\" to activate\n"+
		"tell application \"Terminal\" to do script %q", cmd)
	_ = exec.Command("osascript", "-e", script).Run()
}
