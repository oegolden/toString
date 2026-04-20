"""
content_moderation.py - Content moderation library for harmful content detection.

This module provides utilities to detect and flag potentially harmful content
in posts and messages using heuristic checks and pattern matching.

Features:
- Profanity detection
- Spam pattern detection
- All-caps spam detection
- Excessive special characters detection
- Content length validation
"""

import re
from typing import Tuple, Optional

# Common profanities and offensive words (simple blocklist)
PROFANITIES = {
    # Censored for this example, but in production would be more comprehensive
    "badword1", "badword2", "offensive1", "offensive2",
}

# Spam patterns
SPAM_PATTERNS = [
    r"viagra",
    r"cialis",
    r"casino",
    r"lottery",
    r"click here",
    r"buy now",
    r"limited offer",
    r"http[s]?://",  # URLs without context
]

# Suspicious patterns
SUSPICIOUS_PATTERNS = [
    r"hate",
    r"kill",
    r"attack",
    r"threat",
]


class ContentModerator:
    """Content moderation engine for analyzing post content."""
    
    def __init__(self, enable_profanity_check=True, enable_spam_check=True,
                 enable_suspicious_check=True, max_caps_ratio=0.5):
        """
        Initialize the content moderator.
        
        Args:
            enable_profanity_check: Whether to check for profanity
            enable_spam_check: Whether to check for spam patterns
            enable_suspicious_check: Whether to check for suspicious content
            max_caps_ratio: Maximum allowed ratio of uppercase letters (0-1)
        """
        self.enable_profanity = enable_profanity_check
        self.enable_spam = enable_spam_check
        self.enable_suspicious = enable_suspicious_check
        self.max_caps_ratio = max_caps_ratio
    
    def moderate(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Analyze content for harmful or suspicious patterns.
        
        Args:
            content: The text content to moderate
            
        Returns:
            Tuple of (is_flagged, reason_if_flagged)
            - is_flagged: True if content should be flagged
            - reason_if_flagged: Human-readable reason for flagging
        """
        if not content or len(content.strip()) == 0:
            return False, None
        
        # Check for profanity
        if self.enable_profanity:
            flagged, reason = self._check_profanity(content)
            if flagged:
                return True, reason
        
        # Check for spam patterns
        if self.enable_spam:
            flagged, reason = self._check_spam(content)
            if flagged:
                return True, reason
        
        # Check for suspicious content
        if self.enable_suspicious:
            flagged, reason = self._check_suspicious(content)
            if flagged:
                return True, reason
        
        # Check for excessive caps
        flagged, reason = self._check_excessive_caps(content)
        if flagged:
            return True, reason
        
        # Check for excessive special characters
        flagged, reason = self._check_special_chars(content)
        if flagged:
            return True, reason
        
        return False, None
    
    def _check_profanity(self, content: str) -> Tuple[bool, Optional[str]]:
        """Check for profanity and offensive language."""
        content_lower = content.lower()
        for word in PROFANITIES:
            if word in content_lower:
                return True, f"Content contains inappropriate language"
        return False, None
    
    def _check_spam(self, content: str) -> Tuple[bool, Optional[str]]:
        """Check for common spam patterns."""
        content_lower = content.lower()
        for pattern in SPAM_PATTERNS:
            if re.search(pattern, content_lower):
                return True, f"Content matched spam pattern: {pattern}"
        return False, None
    
    def _check_suspicious(self, content: str) -> Tuple[bool, Optional[str]]:
        """Check for suspicious or harmful keywords."""
        content_lower = content.lower()
        
        # Count suspicious keywords
        suspicious_count = 0
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, content_lower):
                suspicious_count += 1
        
        # Flag if multiple suspicious patterns detected
        if suspicious_count >= 2:
            return True, f"Content contains multiple suspicious keywords (flagged for review)"
        
        return False, None
    
    def _check_excessive_caps(self, content: str) -> Tuple[bool, Optional[str]]:
        """Check for excessive use of capital letters (possible shouting/spam)."""
        alpha_chars = [c for c in content if c.isalpha()]
        if not alpha_chars:
            return False, None
        
        caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if caps_ratio > self.max_caps_ratio:
            return True, f"Content is excessively capitalized ({caps_ratio:.0%})"
        
        return False, None
    
    def _check_special_chars(self, content: str) -> Tuple[bool, Optional[str]]:
        """Check for excessive special characters."""
        special_chars = len([c for c in content if not (c.isalnum() or c.isspace())])
        total_chars = len(content.strip())
        
        if total_chars > 0:
            special_ratio = special_chars / total_chars
            if special_ratio > 0.3:  # More than 30% special characters
                return True, f"Content contains excessive special characters"
        
        return False, None
    
    def get_severity_score(self, content: str) -> float:
        """
        Calculate a severity score for content (0.0 to 1.0).
        
        Args:
            content: The text content to analyze
            
        Returns:
            Severity score where 0.0 = safe, 1.0 = highly suspicious
        """
        score = 0.0
        
        # Check each category and add to score
        if self.enable_profanity and self._check_profanity(content)[0]:
            score += 0.4
        
        if self.enable_spam and self._check_spam(content)[0]:
            score += 0.35
        
        if self.enable_suspicious and self._check_suspicious(content)[0]:
            score += 0.15
        
        if self._check_excessive_caps(content)[0]:
            score += 0.05
        
        if self._check_special_chars(content)[0]:
            score += 0.05
        
        return min(score, 1.0)


# Singleton moderator instance
_moderator = None


def get_moderator() -> ContentModerator:
    """Get or create the global content moderator instance."""
    global _moderator
    if _moderator is None:
        _moderator = ContentModerator()
    return _moderator


def moderate_content(content: str) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to moderate content using the global moderator.
    
    Args:
        content: Text to moderate
        
    Returns:
        Tuple of (is_flagged, reason)
    """
    return get_moderator().moderate(content)


def get_severity_score(content: str) -> float:
    """Get severity score for content."""
    return get_moderator().get_severity_score(content)


if __name__ == "__main__":
    # Test the moderator
    moderator = get_moderator()
    
    test_cases = [
        "Hello, this is a normal post!",
        "BUY VIAGRA NOW!!!",
        "KILL ALL!!!",
        "Visit my casino at http://scam.com",
        "This is a normal message with some context",
        "!!!!!!!!!@@@@@@",
    ]
    
    for test in test_cases:
        flagged, reason = moderator.moderate(test)
        severity = moderator.get_severity_score(test)
        status = "🚩 FLAGGED" if flagged else "✅ SAFE"
        print(f"{status} | Severity: {severity:.2f} | Reason: {reason or 'None'}")
        print(f"   Content: {test[:50]}...")
        print()
