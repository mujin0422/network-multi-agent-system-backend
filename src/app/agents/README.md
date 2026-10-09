# Agents

`agents` là application layer nằm ngoài `domains`. Layer này sở hữu agent
implementations, registry và chính sách orchestration.

```text
agents/
  analyst/          # implementation và prompt của analyst agent
  network/          # implementation và prompt của network agent
  orchestrator/     # routing/supervisor policies
  tools/            # adapter gọi public service của domain
  base.py           # agent contract
  manager.py        # điều phối một lượt thực thi
  registry.py       # đăng ký và lookup agent
  schemas.py        # contract của agent application layer
```

Agent không đặt trong `domains`. Khi agent cần nghiệp vụ mạng, adapter trong
`agents/tools/` gọi `domains/network/service.py`; agent không gọi provider hoặc
Netmiko trực tiếp.
