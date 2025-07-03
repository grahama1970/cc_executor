#!/usr/bin/env python3
"""
Parser for structured self-reflection responses
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ReflectionResult:
    """Structured result from self-reflection parsing"""
    has_initial_response: bool
    has_evaluation: bool
    has_improved_version: bool
    criteria_evaluated: int
    criteria_passed: int
    criteria_failed: int
    improvement_made: bool
    quality_delta: float  # Improvement percentage
    sections: Dict[str, str]
    markers_found: List[str]

class ReflectionParser:
    """Parse self-reflection formatted responses"""
    
    def __init__(self):
        self.section_markers = {
            'initial': [
                'INITIAL RESPONSE:', 
                'Initial Response:', 
                '📝 INITIAL RESPONSE:',
                'VERSION 1',
                'ATTEMPT 1:'
            ],
            'evaluation': [
                'SELF-EVALUATION',
                'EVALUATION',
                '🔍 SELF-EVALUATION',
                'SELF-CHECK',
                'Self-evaluation:'
            ],
            'improved': [
                'IMPROVED VERSION',
                'Improved Version:',
                '📈 IMPROVED VERSION',
                'VERSION 2',
                'ATTEMPT 2:'
            ]
        }
        
        self.checkbox_patterns = [
            r'□\s*(.+?)\s*\[([✓✗])\]',  # □ Criterion [✓/✗]
            r'☐\s*(.+?)\s*\[([✓✗])\]',  # Alternative checkbox
            r'☑\s*(.+?)\s*\[([✓✗])\]',  # Checked checkbox variant
            r'\[\s*([✓✗])\s*\]\s*(.+)',  # [✓] Criterion
            r'✓|✗',  # Just the marks
        ]
    
    def parse(self, response: str) -> ReflectionResult:
        """Parse a self-reflection response"""
        sections = self._extract_sections(response)
        evaluation_stats = self._parse_evaluation(sections.get('evaluation', ''))
        markers = self._find_markers(response)
        
        # Calculate quality delta
        quality_delta = self._calculate_quality_delta(
            sections.get('initial', ''),
            sections.get('improved', '')
        )
        
        return ReflectionResult(
            has_initial_response=bool(sections.get('initial')),
            has_evaluation=bool(sections.get('evaluation')),
            has_improved_version=bool(sections.get('improved')),
            criteria_evaluated=evaluation_stats['total'],
            criteria_passed=evaluation_stats['passed'],
            criteria_failed=evaluation_stats['failed'],
            improvement_made=bool(sections.get('improved')) and evaluation_stats['failed'] > 0,
            quality_delta=quality_delta,
            sections=sections,
            markers_found=markers
        )
    
    def _extract_sections(self, response: str) -> Dict[str, str]:
        """Extract the three main sections"""
        sections = {}
        
        # Find section boundaries
        initial_pos = self._find_section_start(response, 'initial')
        eval_pos = self._find_section_start(response, 'evaluation')
        improved_pos = self._find_section_start(response, 'improved')
        
        # Extract initial response
        if initial_pos is not None:
            end_pos = eval_pos if eval_pos is not None else improved_pos
            if end_pos is None:
                end_pos = len(response)
            sections['initial'] = response[initial_pos:end_pos].strip()
        
        # Extract evaluation
        if eval_pos is not None:
            end_pos = improved_pos if improved_pos is not None else len(response)
            sections['evaluation'] = response[eval_pos:end_pos].strip()
        
        # Extract improved version
        if improved_pos is not None:
            sections['improved'] = response[improved_pos:].strip()
        
        return sections
    
    def _find_section_start(self, response: str, section_type: str) -> Optional[int]:
        """Find the start position of a section"""
        markers = self.section_markers.get(section_type, [])
        
        for marker in markers:
            pos = response.find(marker)
            if pos != -1:
                return pos + len(marker)
        
        return None
    
    def _parse_evaluation(self, eval_section: str) -> Dict[str, int]:
        """Parse evaluation checkboxes"""
        stats = {'total': 0, 'passed': 0, 'failed': 0}
        
        if not eval_section:
            return stats
        
        # Try different checkbox patterns
        for pattern in self.checkbox_patterns[:3]:  # Skip the simple ✓/✗ pattern
            matches = re.findall(pattern, eval_section, re.MULTILINE)
            if matches:
                for match in matches:
                    stats['total'] += 1
                    # Check which group contains the checkmark
                    if isinstance(match, tuple):
                        if '✓' in match:
                            stats['passed'] += 1
                        elif '✗' in match:
                            stats['failed'] += 1
                    elif match == '✓':
                        stats['passed'] += 1
                    elif match == '✗':
                        stats['failed'] += 1
                
                if stats['total'] > 0:
                    break
        
        # Fallback: just count checkmarks
        if stats['total'] == 0:
            stats['passed'] = eval_section.count('✓')
            stats['failed'] = eval_section.count('✗')
            stats['total'] = stats['passed'] + stats['failed']
        
        return stats
    
    def _find_markers(self, response: str) -> List[str]:
        """Find all reflection markers in response"""
        found = []
        
        all_markers = []
        for marker_list in self.section_markers.values():
            all_markers.extend(marker_list)
        
        # Add checkbox markers
        all_markers.extend(['□', '☐', '☑', '✓', '✗'])
        
        for marker in all_markers:
            if marker in response:
                found.append(marker)
        
        return list(set(found))  # Remove duplicates
    
    def _calculate_quality_delta(self, initial: str, improved: str) -> float:
        """Calculate improvement percentage"""
        if not initial or not improved:
            return 0.0
        
        # Simple heuristics for quality improvement
        metrics = {
            'length': len(improved) / max(1, len(initial)),
            'code_blocks': improved.count('```') / max(1, initial.count('```')),
            'examples': improved.lower().count('example') / max(1, initial.lower().count('example')),
            'detail_words': sum(improved.lower().count(w) for w in ['specifically', 'additionally', 'furthermore', 'detailed']) /
                           max(1, sum(initial.lower().count(w) for w in ['specifically', 'additionally', 'furthermore', 'detailed']))
        }
        
        # Average improvement across metrics
        improvements = [max(0, m - 1.0) for m in metrics.values()]
        return sum(improvements) / len(improvements) * 100

    def format_summary(self, result: ReflectionResult) -> str:
        """Format a human-readable summary"""
        lines = ["Self-Reflection Analysis:", "-" * 40]
        
        # Section presence
        lines.append(f"✓ Initial Response: {'Yes' if result.has_initial_response else 'No'}")
        lines.append(f"✓ Self-Evaluation: {'Yes' if result.has_evaluation else 'No'}")
        lines.append(f"✓ Improved Version: {'Yes' if result.has_improved_version else 'No'}")
        
        # Evaluation stats
        if result.criteria_evaluated > 0:
            lines.append(f"\nEvaluation Results:")
            lines.append(f"  Criteria checked: {result.criteria_evaluated}")
            lines.append(f"  Passed: {result.criteria_passed} ✓")
            lines.append(f"  Failed: {result.criteria_failed} ✗")
            lines.append(f"  Success rate: {result.criteria_passed/result.criteria_evaluated*100:.1f}%")
        
        # Improvement
        if result.improvement_made:
            lines.append(f"\nImprovement made: Yes")
            lines.append(f"Quality delta: +{result.quality_delta:.1f}%")
        else:
            lines.append(f"\nImprovement made: No")
        
        # Markers found
        if result.markers_found:
            lines.append(f"\nReflection markers: {', '.join(result.markers_found[:5])}")
        
        return '\n'.join(lines)


# Utility functions for integration
def extract_reflection_quality(response: str) -> Dict[str, any]:
    """Quick utility to extract reflection quality metrics"""
    parser = ReflectionParser()
    result = parser.parse(response)
    
    return {
        'is_reflected': result.has_initial_response and result.has_evaluation,
        'is_improved': result.improvement_made,
        'criteria_success_rate': result.criteria_passed / max(1, result.criteria_evaluated),
        'quality_improvement': result.quality_delta,
        'complete_reflection': all([
            result.has_initial_response,
            result.has_evaluation,
            result.criteria_evaluated > 0
        ])
    }


if __name__ == "__main__":
    # Test the parser
    test_response = """
📝 INITIAL RESPONSE:
The 10th Fibonacci number is 55.

🔍 SELF-EVALUATION (check each box):
□ Stated the specific number requested [✓]
□ Explained how Fibonacci sequence works [✗]
□ Showed the sequence progression [✗]

📈 IMPROVED VERSION (if any ✗ above):
The 10th Fibonacci number is 55.

The Fibonacci sequence starts with 0 and 1, and each subsequent number is the sum of the two preceding ones:
0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55...

So F(10) = 55, where F(8)=21 and F(9)=34, and 21+34=55.
"""
    
    parser = ReflectionParser()
    result = parser.parse(test_response)
    print(parser.format_summary(result))
    
    print("\n" + "=" * 40)
    print("Quick quality check:")
    quality = extract_reflection_quality(test_response)
    for key, value in quality.items():
        print(f"{key}: {value}")