/**
 * Phase 2 Chat Component - Multi-round dialogue with conflict detection
 * Handles chatting, pending confirmation, and search triggering
 */

import { useState, useEffect, useRef } from "react";
import { useAppStore } from "@/lib/store";
import { apiClient } from "@/lib/api-client";
import type { DialogueMessage } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Loader2 } from "lucide-react";

export function Phase2ChatComponent() {
  const {
    sessionId,
    dialogueMessages,
    appendMessage,
    pendingConflict,
    setPendingConflict,
    setAppState,
  } = useAppStore();

  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [dialogueMessages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !sessionId) return;

    setLoading(true);
    const userMessage = inputValue.trim();
    setInputValue("");

    // Add user message to UI
    appendMessage({
      role: "user",
      content: userMessage,
      timestamp: Date.now(),
    });

    try {
      const response = await apiClient.chat(sessionId, userMessage);

      // Add assistant response
      appendMessage({
        role: "agent",
        content: response.reply,
        timestamp: Date.now(),
      });

      // Handle different response statuses
      if (response.status === "pending_confirmation") {
        // Conflict detected - show confirmation dialog
        setPendingConflict({
          conflicting_field: response.conflicting_field || "",
          proposed_value: response.proposed_value,
          reply: response.reply,
        });
        setShowConfirmation(true);
      } else if (response.status === "searching") {
        // FC triggered - transition to search state
        setAppState("SEARCHING");
      }
      // else: status === "chatting" - continue conversation
    } catch (error) {
      console.error("Chat error:", error);
      appendMessage({
        role: "system",
        content: "Sorry, an error occurred. Please try again.",
        timestamp: Date.now(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmConflict = async (confirmed: boolean) => {
    if (!sessionId || !pendingConflict) return;

    setShowConfirmation(false);

    if (confirmed) {
      // User confirmed the change - update requirements and proceed
      try {
        await apiClient.updateRequirements(sessionId, {
          [pendingConflict.conflicting_field]: pendingConflict.proposed_value,
        });
        appendMessage({
          role: "system",
          content: `Updated ${pendingConflict.conflicting_field} to ${pendingConflict.proposed_value}`,
          timestamp: Date.now(),
        });
      } catch (error) {
        console.error("Update failed:", error);
      }
    } else {
      // User rejected the change
      appendMessage({
        role: "system",
        content: `Kept original value for ${pendingConflict.conflicting_field}`,
        timestamp: Date.now(),
      });
    }

    setPendingConflict(null);
  };

  return (
    <div className="w-full max-w-2xl space-y-4">
      {/* Chat Messages */}
      <Card className="h-96 flex flex-col">
        <CardHeader>
          <CardTitle>Chat with Agent</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto space-y-4 mb-4">
          {dialogueMessages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-xs px-4 py-2 rounded-lg ${
                  msg.role === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 text-black"
                }`}
              >
                <p className="text-sm">{msg.content}</p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </CardContent>
      </Card>

      {/* Input Form */}
      <form onSubmit={handleSendMessage} className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Type your message..."
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !inputValue.trim()}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          Send
        </Button>
      </form>

      {/* Conflict Confirmation Dialog */}
      <AlertDialog open={showConfirmation} onOpenChange={setShowConfirmation}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Change</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingConflict?.reply}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="bg-gray-100 p-4 rounded">
            <p className="text-sm">
              <strong>Field:</strong> {pendingConflict?.conflicting_field}
            </p>
            <p className="text-sm">
              <strong>New Value:</strong> {String(pendingConflict?.proposed_value)}
            </p>
          </div>
          <div className="flex gap-3">
            <AlertDialogCancel onClick={() => handleConfirmConflict(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={() => handleConfirmConflict(true)}>
              Confirm
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

