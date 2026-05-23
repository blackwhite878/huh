/**
 * Results Display Component - Shows property batch results
 * Handles rejection, next batch fetch, and tier display
 */

import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { usePropertyRejection, useNPPLearning, useNextBatch } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import type { PropertyResult } from "@/lib/types";
import { ThumbsUp, ThumbsDown, MoreHorizontal } from "lucide-react";

export function ResultsDisplayComponent() {
  const {
    sessionId,
    currentBatch,
    batchIndex,
    totalAvailable,
    hasMore,
    tier3Triggered,
    rejectionCount,
    setAppState,
  } = useAppStore();

  const { rejectProperty } = usePropertyRejection(sessionId);
  const { triggerNPPLearning } = useNPPLearning(sessionId);
  const { fetchNextBatch } = useNextBatch(sessionId);

  const [selectedProperty, setSelectedProperty] = useState<PropertyResult | null>(null);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [rejectedCount, setRejectedCount] = useState(0);

  if (tier3Triggered) {
    return (
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>No Results Found</CardTitle>
          <CardDescription>
            We couldn't find any properties matching your criteria even after expanding the search area.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => setAppState("ACTION_REQUIRED_UI")}>
            Adjust Preferences
          </Button>
        </CardContent>
      </Card>
    );
  }

  const handleReject = async () => {
    if (!selectedProperty || !rejectReason.trim() || !sessionId) return;

    await rejectProperty(selectedProperty.property_id, rejectReason);
    setRejectedCount((prev) => prev + 1);
    setShowRejectDialog(false);
    setRejectReason("");
    setSelectedProperty(null);

    // Check if all properties in batch are rejected
    if (rejectedCount + 1 >= currentBatch.length) {
      // All rejected - trigger NPP learning
      await triggerNPPLearning();
    }
  };

  const handleNextBatch = async () => {
    await fetchNextBatch();
  };

  return (
    <div className="w-full space-y-4">
      {/* Batch Info */}
      <div className="text-sm text-gray-600">
        Batch {batchIndex} of {Math.ceil(totalAvailable / 5)} |
        {totalAvailable} total available
      </div>

      {/* Property Cards */}
      <div className="grid gap-4">
        {currentBatch.map((property) => (
          <PropertyCard
            key={property.property_id}
            property={property}
            onReject={(prop) => {
              setSelectedProperty(prop);
              setShowRejectDialog(true);
            }}
          />
        ))}
      </div>

      {/* Navigation */}
      <div className="flex gap-2 justify-between">
        <div>
          {rejectedCount > 0 && (
            <span className="text-sm text-gray-600">
              Rejected: {rejectedCount}/{currentBatch.length}
            </span>
          )}
        </div>
        <Button
          onClick={handleNextBatch}
          disabled={!hasMore}
          variant="outline"
        >
          {hasMore ? "Next Batch" : "No More Results"}
        </Button>
      </div>

      {/* Reject Dialog */}
      <AlertDialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Property</AlertDialogTitle>
            <AlertDialogDescription>
              {selectedProperty?.title}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Reason for rejection</label>
              <input
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g., too high floor, near industrial area"
                className="w-full mt-2 px-3 py-2 border rounded"
              />
            </div>
          </div>
          <div className="flex gap-3">
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleReject}>
              Reject
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

/**
 * Individual Property Card Component
 */
function PropertyCard({
  property,
  onReject,
}: {
  property: PropertyResult;
  onReject: (prop: PropertyResult) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg">{property.title}</CardTitle>
            <CardDescription>{property.location}</CardDescription>
          </div>
          <Badge variant={property.tier === "tier_1" ? "default" : "secondary"}>
            {property.tier === "tier_1" ? "Top Match" : "Alternative"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Price */}
        <div className="flex justify-between items-center">
          <span className="font-semibold">MYR {property.price.toLocaleString()}</span>
        </div>

        {/* Tags */}
        {property.feature_tags && property.feature_tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {property.feature_tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* AI Remarks */}
        {property.ai_remarks && (
          <div className="bg-blue-50 p-3 rounded text-sm">
            <p className="text-gray-700">{property.ai_remarks}</p>
          </div>
        )}

        {/* Missing Features (Tier 2) */}
        {property.missing_features && property.missing_features.length > 0 && (
          <div className="bg-yellow-50 p-3 rounded text-sm">
            <p className="font-medium text-yellow-900 mb-1">Missing Features:</p>
            <ul className="list-disc list-inside text-yellow-800">
              {property.missing_features.map((feat, idx) => (
                <li key={idx}>{feat}</li>
              ))}
            </ul>
            {property.remedy && (
              <p className="mt-2 text-yellow-800">
                <strong>Remedy:</strong> {property.remedy}
              </p>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1"
            onClick={() => onReject(property)}
          >
            <ThumbsDown className="mr-1 h-4 w-4" />
            Not Interested
          </Button>
          {property.url && (
            <Button size="sm" variant="outline" asChild>
              <a href={property.url} target="_blank" rel="noopener noreferrer">
                <MoreHorizontal className="h-4 w-4" />
              </a>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

