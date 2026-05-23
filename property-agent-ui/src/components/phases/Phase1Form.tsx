/**
 * Phase 1 Form Component - Profiling/Semantic Alignment Phase
 * Collects user requirements and launches async semantic alignment
 */

import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { useSemanticAlignment } from "@/hooks/use-api";
import { apiClient } from "@/lib/api-client";
import type { Phase1Form } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

export function Phase1FormComponent() {
  const { setSessionId, setPhase1Form, setAppState } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<Phase1Form>({
    budget: 500000,
    agent_style: "professional",
    target: "condo in Johor Bahru",
    identity: "first_time_buyer",
    gender: "prefer_not_to_say",
    description: "",
  });

  const handleInputChange = (field: keyof Phase1Form, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Initialize session - async launches semantic alignment
      const response = await apiClient.initSession(formData);
      setSessionId(response.session_id);
      setPhase1Form(formData);

      // Transition to semantic alignment polling state
      setAppState("SEMANTIC_ALIGNING");

      // useSemanticAlignment hook will handle polling
    } catch (error) {
      console.error("Session init failed:", error);
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>Property Search Profile</CardTitle>
        <CardDescription>
          Tell us about your ideal property and preferences
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Budget */}
          <div className="space-y-2">
            <Label htmlFor="budget">Budget (MYR)</Label>
            <Input
              id="budget"
              type="number"
              value={formData.budget}
              onChange={(e) => handleInputChange("budget", Number(e.target.value))}
              placeholder="500000"
            />
          </div>

          {/* Target */}
          <div className="space-y-2">
            <Label htmlFor="target">Target Property</Label>
            <Input
              id="target"
              value={formData.target}
              onChange={(e) => handleInputChange("target", e.target.value)}
              placeholder="e.g., condo in Johor Bahru"
            />
          </div>

          {/* Agent Style */}
          <div className="space-y-2">
            <Label>Agent Style</Label>
            <Select
              value={formData.agent_style}
              onValueChange={(value) => handleInputChange("agent_style", value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="professional">Professional</SelectItem>
                <SelectItem value="friendly">Friendly</SelectItem>
                <SelectItem value="active">Active</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Identity */}
          <div className="space-y-2">
            <Label>Buyer Profile</Label>
            <RadioGroup
              value={formData.identity}
              onValueChange={(value) => handleInputChange("identity", value)}
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="first_time_buyer" id="first_time" />
                <Label htmlFor="first_time" className="font-normal cursor-pointer">
                  First Time Buyer
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="investor" id="investor" />
                <Label htmlFor="investor" className="font-normal cursor-pointer">
                  Investor
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="upgrader" id="upgrader" />
                <Label htmlFor="upgrader" className="font-normal cursor-pointer">
                  Upgrader
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Gender */}
          <div className="space-y-2">
            <Label>Gender (Optional)</Label>
            <RadioGroup
              value={formData.gender}
              onValueChange={(value) => handleInputChange("gender", value)}
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="female" id="female" />
                <Label htmlFor="female" className="font-normal cursor-pointer">
                  Female
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="male" id="male" />
                <Label htmlFor="male" className="font-normal cursor-pointer">
                  Male
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="prefer_not_to_say" id="prefer_not" />
                <Label htmlFor="prefer_not" className="font-normal cursor-pointer">
                  Prefer Not to Say
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Additional Preferences</Label>
            <Input
              id="description"
              value={formData.description}
              onChange={(e) => handleInputChange("description", e.target.value)}
              placeholder="e.g., near school, low maintenance fees"
            />
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Initializing..." : "Start Search"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

