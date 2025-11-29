import re
import time

from typing import Tuple


def call_llm_safe(agent, temperature: float = 0.0, use_thinking: bool = False) -> str:
    # Retry if fails
    max_retries = 3  # Set the maximum number of retries
    attempt = 0
    response = ""
    while attempt < max_retries:
        try:
            response = agent.get_response(
                temperature=temperature, use_thinking=use_thinking
            )
            assert response is not None, "Response from agent should not be None"
            print("Response success!")
            break  # If successful, break out of the loop
        except Exception as e:
            attempt += 1
            print(f"Attempt {attempt} failed: {e}")
            if attempt == max_retries:
                print("Max retries reached. Handling failure.")
        time.sleep(1.0)
    return response if response is not None else ""


def split_thinking_response(full_response: str) -> Tuple[str, str]:
    try:
        # Extract thoughts section
        thoughts_match = re.search(
            r"<thoughts>(.*?)</thoughts>", full_response, re.DOTALL
        )
        thoughts = thoughts_match.group(1).strip()
        # Extract answer section
        answer_match = re.search(r"<answer>(.*?)</answer>", full_response, re.DOTALL)
        answer = answer_match.group(1).strip()
        return answer, thoughts
    except Exception as e:
        return full_response, ""


def parse_single_code_from_string(input_string):
    input_string = input_string.strip()
    if input_string.strip() in ["WAIT", "DONE", "FAIL"]:
        return input_string.strip()

    # This regular expression will match both ```code``` and ```python code```
    # and capture the `code` part. It uses a non-greedy match for the content inside.
    pattern = r"```(?:\w+\s+)?(.*?)```"
    # Find all non-overlapping matches in the string
    matches = re.findall(pattern, input_string, re.DOTALL)

    # The regex above captures the content inside the triple backticks.
    # The `re.DOTALL` flag allows the dot `.` to match newline characters as well,
    # so the code inside backticks can span multiple lines.

    # matches now contains all the captured code snippets

    codes = []

    for match in matches:
        match = match.strip()
        commands = [
            "WAIT",
            "DONE",
            "FAIL",
        ]  # fixme: updates this part when we have more commands

        if match in commands:
            codes.append(match.strip())
        elif match.split("\n")[-1] in commands:
            if len(match.split("\n")) > 1:
                codes.append("\n".join(match.split("\n")[:-1]))
            codes.append(match.split("\n")[-1])
        else:
            codes.append(match)

    if len(codes) <= 0:
        return "fail"
    return codes[0]


def sanitize_code(code_str: str) -> str:
    """
    过滤代码中的不安全部分，防止潜在的XSS攻击和注入风险
    
    Args:
        code_str: 需要清理的代码字符串
    
    Returns:
        清理后的安全代码字符串
    """
    import re
    import logging
    
    # 输入验证
    if not isinstance(code_str, str):
        logging.warning(f"sanitize_code: 输入不是字符串类型: {type(code_str)}")
        return ""
    
    # 去除首尾空白字符
    sanitized = code_str.strip()
    
    # 替换潜在危险的HTML标签和JavaScript代码
    # 移除script标签及其内容
    sanitized = re.sub(r'<\s*script[^>]*>.*?</\s*script\s*>', '', sanitized, flags=re.DOTALL)
    
    # 转义HTML特殊字符
    sanitized = sanitized.replace('&', '&amp;')
    sanitized = sanitized.replace('<', '&lt;')
    sanitized = sanitized.replace('>', '&gt;')
    
    # 替换引号，统一使用单引号
    sanitized = sanitized.replace('"', "'")
    
    # 移除潜在的危险字符序列
    dangerous_patterns = [
        r'javascript:',
        r'vbscript:',
        r'data:text/html',
        r'on\w+\s*='  # 移除事件处理器属性
    ]
    
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
    
    logging.debug(f"sanitize_code: 清理前长度={len(code_str)}, 清理后长度={len(sanitized)}")
    return sanitized


def extract_first_agent_function(code_string):
    # Regular expression pattern to match 'agent' functions with any arguments, including nested parentheses
    pattern = r'agent\.[a-zA-Z_]+\((?:[^()\'"]|\'[^\']*\'|"[^"]*")*\)'

    # Find all matches in the string
    matches = re.findall(pattern, code_string)

    # Return the first match if found, otherwise return None
    return matches[0] if matches else None
