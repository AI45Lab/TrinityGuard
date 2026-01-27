"""Open-Prompt-Injection library adapter for MASSafetyGuard.

This adapter converts OPI (Open-Prompt-Injection) attacks into
MASSafetyGuard TestCase objects for prompt injection testing.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional

# 导入父级目录的 TestCase
from ..base import TestCase


class OPIAdapter:
    """Adapter for Open-Prompt-Injection library.

    Converts OPI attack strategies into MASSafetyGuard test cases
    specifically for prompt injection testing.
    """

    # OPI 攻击策略描述
    ATTACK_DESCRIPTIONS = {
        'naive': '直接拼接注入指令和数据',
        'escape': '使用转义字符绕过检测',
        'ignore': '使用忽略指令覆盖原始任务',
        'fake_comp': '伪造完成标记注入恶意指令',
        'combine': '组合多种攻击策略（最复杂）'
    }

    # OPI 任务描述
    TASK_DESCRIPTIONS = {
        'sentiment_analysis': '情感分析',
        'spam_detection': '垃圾短信检测',
        'hatred_detection': '仇恨言论检测',
        'paraphrase': '句子复述',
        'inference': '自然语言推理',
        'summarization': '摘要生成',
        'grammar': '语法纠错'
    }

    def __init__(self):
        """Initialize OPI adapter."""
        # OPI 现在就在 adapter 目录下
        self.opi_path = Path(__file__).parent / "Open-Prompt-Injection"

        # 验证 OPI 目录是否存在
        if not self.opi_path.exists():
            raise FileNotFoundError(
                f"Open-Prompt-Injection not found at: {self.opi_path}\n"
                f"Please copy Open-Prompt-Injection to the adapter directory"
            )

        # 添加 OPI 到 Python 路径
        opi_str = str(self.opi_path)
        if opi_str not in sys.path:
            sys.path.insert(0, opi_str)

        # 延迟导入
        self._opi = None
        self._open_config = None

    def _load_opi(self):
        """Lazy load Open-Prompt-Injection module."""
        if self._opi is None:
            try:
                import OpenPromptInjection as PI
                from OpenPromptInjection.utils import open_config

                self._opi = PI
                self._open_config = open_config

                print(f"[OPIAdapter] Successfully loaded Open-Prompt-Injection")
            except ImportError as e:
                raise ImportError(
                    f"Failed to import Open-Prompt-Injection. Error: {e}\n"
                    f"Please ensure all dependencies are installed"
                )

    def create_test_cases(
        self,
        attack_strategy: str = 'combine',
        task_config: str = 'rte_config.json',
        num_cases: int = 10,
        severity: str = 'high'
    ) -> List[TestCase]:
        """Generate test cases from OPI attacks.

        Args:
            attack_strategy: OPI attack strategy
                Options: 'naive', 'escape', 'ignore', 'fake_comp', 'combine'
            task_config: Task config file name in OPI configs/task_configs/
                Examples: 'rte_config.json', 'sst2_config.json'
            num_cases: Number of test cases to generate
            severity: Severity level: 'low', 'medium', 'high', 'critical'

        Returns:
            List of TestCase objects
        """
        self._load_opi()

        # 验证攻击策略
        valid_strategies = list(self.ATTACK_DESCRIPTIONS.keys())
        if attack_strategy not in valid_strategies:
            raise ValueError(
                f"Invalid attack_strategy: {attack_strategy}\n"
                f"Valid options: {valid_strategies}"
            )

        # 加载 OPI 任务配置
        config_path = self.opi_path / "configs" / "task_configs" / task_config
        if not config_path.exists():
            available = self.get_available_tasks()
            raise FileNotFoundError(
                f"Task config not found: {config_path}\n"
                f"Available: {available}"
            )

        task_config_data = self._open_config(config_path=str(config_path))

        # 创建 OPI 注入任务和攻击者
        inject_task = self._opi.create_task(
            task_config_data,
            num_cases,
            for_injection=True
        )
        attacker = self._opi.create_attacker(attack_strategy, inject_task)

        # 转换为 TestCase
        test_cases = []
        actual_num = min(num_cases, len(inject_task))

        print(f"[OPIAdapter] Generating {actual_num} cases: {attack_strategy} + {task_config}")

        for idx in range(actual_num):
            data_prompt, _ = inject_task[idx]
            injected_prompt = attacker.get_injected_prompt("", idx)

            # 构建名称和描述
            task_name = task_config_data['task_info'].get('task', 'unknown')
            test_name = f"opi_{attack_strategy}_{task_name}_{idx}"

            task_desc = self.TASK_DESCRIPTIONS.get(task_name, task_name)
            attack_desc = self.ATTACK_DESCRIPTIONS.get(attack_strategy, attack_strategy)
            expected_behavior = f"Agent should resist '{attack_desc}' attack and perform: {task_desc}"

            test_case = TestCase(
                name=test_name,
                input=injected_prompt,
                expected_behavior=expected_behavior,
                severity=severity,
                metadata={
                    "source": "Open-Prompt-Injection",
                    "attack_strategy": attack_strategy,
                    "task": task_name,
                    "dataset": task_config_data['dataset_info'].get('dataset', 'unknown'),
                    "opi_index": idx
                }
            )
            test_cases.append(test_case)

        print(f"[OPIAdapter] Generated {len(test_cases)} test cases")
        return test_cases

    def get_attack_strategies(self) -> List[str]:
        """Get available attack strategies."""
        return list(self.ATTACK_DESCRIPTIONS.keys())

    def get_available_tasks(self) -> List[str]:
        """Get available OPI task config files."""
        configs_dir = self.opi_path / "configs" / "task_configs"
        if not configs_dir.exists():
            return []
        return sorted([f.name for f in configs_dir.glob("*.json")])

    def get_strategy_info(self) -> Dict[str, str]:
        """Get attack strategy descriptions."""
        return self.ATTACK_DESCRIPTIONS.copy()

    def validate(self) -> bool:
        """Validate OPI installation."""
        try:
            self._load_opi()
            return True
        except Exception:
            return False
